"""Claude Code session log parser.

Scans ~/.claude/projects/<encoded-cwd>/<session-uuid>.jsonl.
Only `type == "assistant"` records carry token usage; everything else is skipped.
Dedup is by message.id (msg_xxx) — see cc-switch session_usage.rs for prior art.

Incremental optimization: files with unchanged mtime are skipped. When a file
*has* changed, we re-read it from line 1 (no offset tracking) and rely on
message.id dedup so the daily 14:00 cron always captures tail tokens written
after the previous sync — see state.py for the full rationale.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterator

from . import UsageRecord


def projects_dir() -> Path:
    return Path(os.environ.get("CLAUDE_HOME", Path.home() / ".claude")) / "projects"


def collect_files() -> list[Path]:
    root = projects_dir()
    if not root.is_dir():
        return []
    files: list[Path] = []
    for project in root.iterdir():
        if not project.is_dir():
            continue
        files.extend(p for p in project.iterdir() if p.suffix == ".jsonl")
    return files


def parse_file(path: Path) -> Iterator[UsageRecord]:
    """Yield UsageRecord for each assistant turn in this file.

    Re-reads the file fully on every sync. Per-message dedup (msg.id) prevents
    double-counting across runs, and the daily aggregator filters by date.
    """
    if not path.exists():
        return

    # Per-file dedup: same message.id can appear multiple times in JSONL
    # (e.g. retried turns). Keep the one with stop_reason; fall back to latest.
    seen: dict[str, tuple[bool, UsageRecord]] = {}
    last_session_id: str | None = None

    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            if last_session_id is None:
                sid = rec.get("sessionId")
                if sid:
                    last_session_id = sid

            if rec.get("type") != "assistant":
                continue

            msg = rec.get("message") or {}
            msg_id = msg.get("id")
            usage = msg.get("usage")
            if not msg_id or not usage:
                continue

            model = msg.get("model") or "unknown"
            stop_reason = msg.get("stop_reason")

            # We track Skill invocations only (e.g. polymath-customer-brief,
            # lark-im, anthropic-skills:pptx) — not built-in tools like Bash/Edit
            # which dominate but say little about how the skill pack is used.
            skills: list[str] = []
            for block in msg.get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_use":
                    continue
                if block.get("name") != "Skill":
                    continue
                skill_name = (block.get("input") or {}).get("skill")
                if skill_name:
                    skills.append(skill_name)

            ur = UsageRecord(
                agent="claude-code",
                timestamp=rec.get("timestamp", ""),
                session_id=last_session_id or "",
                model=model,
                input_tokens=int(usage.get("input_tokens") or 0),
                output_tokens=int(usage.get("output_tokens") or 0),
                cache_read_tokens=int(usage.get("cache_read_input_tokens") or 0),
                cache_creation_tokens=int(usage.get("cache_creation_input_tokens") or 0),
                dedup_id=msg_id,
                skills=skills,
            )

            existing = seen.get(msg_id)
            if existing is None or (not existing[0] and stop_reason):
                seen[msg_id] = (bool(stop_reason), ur)

    yield from (rec for _, rec in seen.values())


def parse_all() -> Iterator[UsageRecord]:
    for path in collect_files():
        yield from parse_file(path)
