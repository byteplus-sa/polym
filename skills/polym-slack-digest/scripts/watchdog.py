#!/usr/bin/env python3
"""T+20min watchdog: verify today's doc was generated. Self-retry up to 3 times on failure."""
import argparse, datetime, json, os, subprocess, sys, time

HOME = os.path.expanduser("~")
ROOT = os.environ.get("SLACK_DIGEST_HOME") or os.path.join(HOME, ".slack-daily-digest")
INDEX_JSON = os.path.join(ROOT, "index.json")

REQUIRED_SECTIONS = [
    "Executive Summary",
    "Highlights",
    "TODO",
    "Pipeline",
    "Risk",
    "By Channel",
    "Statistics",
]

BACKOFF = [60, 300, 900]  # seconds


def log(run_dir, msg):
    p = os.path.join(run_dir, "watchdog.log")
    with open(p, "a") as f:
        f.write(f"[{datetime.datetime.utcnow().isoformat()}Z] {msg}\n")


def _lark_cli():
    configured = os.environ.get("LARK_CLI_PATH")
    if configured:
        return configured
    homebrew = "/opt/homebrew/bin/lark-cli"
    if os.path.exists(homebrew):
        return homebrew
    return "lark-cli"


def read_doc(doc_url, skill_path=None):
    cli = _lark_cli()
    cmd = [cli, "docs", "+fetch", "--doc", doc_url, "--format", "json"]
    return subprocess.run(cmd, capture_output=True, text=True)


def _extract_markdown(result):
    try:
        data = json.loads(result.stdout)
        return data.get("data", {}).get("markdown", result.stdout)
    except Exception:
        return result.stdout


def find_today_in_index(index_url, date, skill_path=None):
    r = read_doc(index_url)
    if r.returncode != 0:
        return None, f"read index failed: {r.stderr}"
    text = _extract_markdown(r)
    if date not in text:
        return None, f"date {date} not in index"
    import re
    m = re.search(rf"\*\*{re.escape(date)}\*\*.*?\((https://[^)]+)\)", text)
    if m:
        return m.group(1), None
    return None, f"date {date} present but doc URL not parsable"


def check_doc_sections(doc_url, slot, skill_path=None):
    r = read_doc(doc_url)
    if r.returncode != 0:
        return False, f"read doc failed: {r.stderr}"
    body = _extract_markdown(r)
    missing = [s for s in REQUIRED_SECTIONS if s not in body]
    if missing:
        return False, f"missing sections: {missing}"
    if slot.startswith("16") and "placeholder, to be filled" in body:
        return False, "16:00 section still has placeholder"
    return True, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--slot", required=True, help="HH:MM e.g. 11:00 / 16:00")
    ap.add_argument("--skill-path", default="/data/plugins/market/lark-docs-skill/skills/lark-docs-skill",
                    help="path to lark-docs-skill (for read-doc CLI)")
    args = ap.parse_args()

    run_dir = os.path.join(ROOT, "runs", args.date)
    os.makedirs(run_dir, exist_ok=True)

    if not os.path.exists(INDEX_JSON):
        log(run_dir, "ERR: index.json missing — onboarding incomplete")
        return 2
    with open(INDEX_JSON) as f:
        idx = json.load(f)
    index_url = idx.get("index_doc_url")
    if not index_url:
        msg = "Lark index document is not configured yet. Please complete Lark setup first."
        log(run_dir, f"ERR: {msg}")
        print(msg, file=sys.stderr)
        return 2

    for attempt in range(1, 4):
        log(run_dir, f"check attempt {attempt}")
        doc_url, err = find_today_in_index(index_url, args.date, args.skill_path)
        if err:
            log(run_dir, f"index check fail: {err}")
        else:
            ok, msg = check_doc_sections(doc_url, args.slot, args.skill_path)
            if ok:
                log(run_dir, f"OK doc_url={doc_url}")
                print(json.dumps({"ok": True, "doc_url": doc_url}))
                return 0
            log(run_dir, f"section check fail: {msg}")

        if attempt < 3:
            wait = BACKOFF[attempt - 1]
            log(run_dir, f"retry in {wait}s; agent should re-run run_digest.py first")
            # Surface a JSON to caller so the agent can re-trigger the daily run pipeline
            print(json.dumps({
                "ok": False,
                "attempt": attempt,
                "next_action": "rerun_daily",
                "wait_seconds": wait,
                "date": args.date,
                "slot": args.slot,
            }))
            time.sleep(wait)
        else:
            log(run_dir, "max retries reached — escalate to user")
            print(json.dumps({
                "ok": False,
                "attempt": attempt,
                "next_action": "escalate",
                "reason": "max retries reached",
            }))
            return 1


if __name__ == "__main__":
    sys.exit(main())
