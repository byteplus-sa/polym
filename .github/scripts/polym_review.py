#!/usr/bin/env python3
"""Polym PR reviewer.

Reads the PR diff + the repo's own rules (CONTRIBUTING.md, manifest.schema.yaml,
profile.schema.yaml), asks an OpenAI-compatible LLM for an advisory review, and
posts the result as a PR comment.

Env vars required:
- REPO, PR_NUMBER, GH_TOKEN       (set by the workflow)
- POLYM_LLM_BASE_URL              OpenAI-compatible chat-completions root
                                  (e.g. https://ark.ap-southeast-1.bytepluses.com/api/v3)
- POLYM_LLM_API_KEY               bearer token for that endpoint
- POLYM_LLM_MODEL                 model id (e.g. doubao-seed-2.0-pro)

Optional:
- EVENT_NAME, TRIGGER_COMMENT     to surface a follow-up question from @polym mentions
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from openai import OpenAI

REPO_RULE_FILES = [
    "CONTRIBUTING.md",
    "manifest.schema.yaml",
    "profile.schema.yaml",
    "README.md",
]

# Hard caps to stay inside reasonable context windows.
MAX_DIFF_CHARS = 80_000
MAX_RULE_CHARS = 8_000
MAX_COMMENT_BODY = 60_000  # GitHub limit is 65536

SYSTEM_PROMPT = """You are Polym, an advisory PR reviewer for the polym repo (byteplus-sa/polym).

Your job: read the PR diff and report whether it follows the repo's own conventions, which are defined in CONTRIBUTING.md, manifest.schema.yaml and profile.schema.yaml (provided to you in the user message). Do not invent rules. Do not enforce general style preferences beyond what those files say.

Format the response exactly like this Markdown:

## Polym review

**Verdict:** one of — 👍 Ready to merge / 🤔 Some suggestions / 🛑 Has blockers

### Findings
- bullet list. Each bullet starts with a tag: `[blocker]`, `[suggestion]`, or `[nit]`.
- Reference files as `path/to/file.ext` (and `:line` when helpful).
- Be specific; don't repeat what's obvious from the diff.

### Compliance checks
A short checklist. For each item write ✅ / ⚠️ / ❌ followed by one short clause.
Only include items relevant to this PR's diff. Typical items:
- manifest.yaml required fields present (name, version, stage, owners, description_for_install)
- SKILL.md description ≤ 250 chars and starts with a verb
- folder name matches manifest `name` and starts with `polym-`
- tests/smoke.sh exists and is executable
- CHANGELOG.md has an entry for the new version
- new skills don't `Read` / `source` files from other skills' folders
- triggers don't obviously collide with existing skills

Style rules:
- Keep the whole review under 500 words.
- Don't praise. Don't restate the PR description.
- If the diff is doc-only or doesn't touch any skill, skip the compliance checklist and just give findings.
- If you have no blockers and no suggestions, say so and recommend merge.
"""


def run(cmd: list[str], check: bool = True) -> str:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if check and res.returncode:
        print(f"Command failed ({res.returncode}): {' '.join(cmd)}", file=sys.stderr)
        if res.stdout:
            print("stdout:", file=sys.stderr)
            print(res.stdout, file=sys.stderr)
        if res.stderr:
            print("stderr:", file=sys.stderr)
            print(res.stderr, file=sys.stderr)
        raise subprocess.CalledProcessError(
            res.returncode,
            res.args,
            output=res.stdout,
            stderr=res.stderr,
        )
    return res.stdout


def fetch_pr_diff(repo: str, pr_number: str) -> str:
    return run(["gh", "pr", "diff", pr_number, "--repo", repo])


def fetch_pr_meta(repo: str, pr_number: str) -> dict:
    pr = json.loads(run(["gh", "api", f"repos/{repo}/pulls/{pr_number}"]))
    files: list[dict] = []
    page = 1
    while True:
        page_files = json.loads(run([
            "gh",
            "api",
            f"repos/{repo}/pulls/{pr_number}/files?per_page=100&page={page}",
        ]))
        files.extend({
            "path": item.get("filename"),
            "additions": item.get("additions", 0),
            "deletions": item.get("deletions", 0),
        } for item in page_files)
        if len(page_files) < 100:
            break
        page += 1

    return {
        "title": pr.get("title"),
        "body": pr.get("body"),
        "author": {"login": (pr.get("user") or {}).get("login")},
        "baseRefName": (pr.get("base") or {}).get("ref"),
        "headRefName": (pr.get("head") or {}).get("ref"),
        "additions": pr.get("additions", 0),
        "deletions": pr.get("deletions", 0),
        "files": files,
    }


def read_repo_rules() -> dict[str, str]:
    rules: dict[str, str] = {}
    for name in REPO_RULE_FILES:
        p = Path(name)
        if p.exists():
            text = p.read_text(encoding="utf-8", errors="replace")
            rules[name] = text[:MAX_RULE_CHARS]
    return rules


def build_user_prompt(
    meta: dict,
    rules: dict[str, str],
    diff: str,
    follow_up: str | None,
) -> str:
    pieces: list[str] = []
    pieces.append("## PR metadata")
    pieces.append(f"- Title: {meta.get('title')}")
    pieces.append(f"- Author: @{(meta.get('author') or {}).get('login', '?')}")
    pieces.append(f"- Branch: `{meta.get('baseRefName')}` ← `{meta.get('headRefName')}`")
    pieces.append(f"- Stats: +{meta.get('additions', 0)} / -{meta.get('deletions', 0)} across {len(meta.get('files') or [])} files")
    pieces.append("")
    pieces.append("## PR body")
    pieces.append(meta.get("body") or "_(empty)_")
    pieces.append("")
    pieces.append("## Repo rules (cite these in findings; ignore anything not in here)")
    for name, content in rules.items():
        pieces.append(f"### `{name}`")
        pieces.append("```")
        pieces.append(content)
        pieces.append("```")
        pieces.append("")
    if follow_up:
        pieces.append("## Follow-up from PR comment")
        pieces.append(
            "A reviewer pinged @polym with this question. Address it specifically in your review "
            "while still doing the full compliance check."
        )
        pieces.append("```")
        pieces.append(follow_up)
        pieces.append("```")
        pieces.append("")
    truncated = diff[:MAX_DIFF_CHARS]
    if len(diff) > MAX_DIFF_CHARS:
        truncated += f"\n\n[... diff truncated at {MAX_DIFF_CHARS:,} chars; total was {len(diff):,} ...]"
    pieces.append("## Diff")
    pieces.append("```diff")
    pieces.append(truncated)
    pieces.append("```")
    return "\n".join(pieces)


def call_llm(user_prompt: str) -> str:
    base_url = os.environ.get("POLYM_LLM_BASE_URL", "").strip()
    api_key = os.environ.get("POLYM_LLM_API_KEY", "").strip()
    model = os.environ.get("POLYM_LLM_MODEL", "").strip()
    missing = [name for name, val in [
        ("POLYM_LLM_BASE_URL", base_url),
        ("POLYM_LLM_API_KEY", api_key),
        ("POLYM_LLM_MODEL", model),
    ] if not val]
    if missing:
        raise SystemExit(
            "Missing required workflow inputs: "
            + ", ".join(missing)
            + ". Set these as repo secrets at "
            "Settings → Secrets and variables → Actions → Secrets."
        )
    client = OpenAI(base_url=base_url, api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()


def post_comment(repo: str, pr_number: str, body: str) -> None:
    if len(body) > MAX_COMMENT_BODY:
        body = body[: MAX_COMMENT_BODY - 200] + "\n\n_[truncated for GitHub comment limit]_"
    subprocess.run(
        ["gh", "pr", "comment", pr_number, "--repo", repo, "--body", body],
        check=True,
    )


def main() -> None:
    repo = os.environ["REPO"]
    pr_number = os.environ["PR_NUMBER"]
    event_name = os.environ.get("EVENT_NAME", "")
    trigger_comment = os.environ.get("TRIGGER_COMMENT", "").strip()

    follow_up: str | None = None
    if event_name == "issue_comment" and "@polym" in trigger_comment:
        follow_up = trigger_comment

    diff = fetch_pr_diff(repo, pr_number)
    if not diff.strip():
        print("Empty diff; nothing to review.", file=sys.stderr)
        return

    meta = fetch_pr_meta(repo, pr_number)
    rules = read_repo_rules()

    user_prompt = build_user_prompt(meta, rules, diff, follow_up)
    review = call_llm(user_prompt)

    footer = (
        "\n\n---\n"
        "_Advisory review by [`polym-pr-review`](.github/workflows/polym-pr-review.yml). "
        "Mention `@polym` in a comment to re-run with a follow-up question._"
    )
    post_comment(repo, pr_number, review + footer)
    print("Posted review.")


if __name__ == "__main__":
    main()
