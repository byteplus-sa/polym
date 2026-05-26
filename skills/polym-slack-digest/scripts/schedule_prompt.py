#!/usr/bin/env python3
"""One-time post-setup schedule prompt."""
import datetime
import json
import os
from status_renderer import render_status

HOME = os.path.expanduser("~")
ROOT = os.environ.get("SLACK_DIGEST_HOME") or os.path.join(HOME, ".slack-daily-digest")
SCHEDULE_PROMPT_PATH = os.path.join(ROOT, "schedule_prompt.json")


def schedule_prompt_once():
    if os.path.exists(SCHEDULE_PROMPT_PATH):
        return
    os.makedirs(ROOT, exist_ok=True)
    payload = {
        "prompted_at": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "status": "schedule_prompted",
    }
    tmp = SCHEDULE_PROMPT_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    os.chmod(tmp, 0o600)
    os.replace(tmp, SCHEDULE_PROMPT_PATH)
    render_status("schedule question", schedule_question=True)
