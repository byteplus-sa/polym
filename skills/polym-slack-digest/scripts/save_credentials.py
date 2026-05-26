#!/usr/bin/env python3
"""Persist Slack + Lark credentials to $SLACK_DIGEST_HOME/credentials.json (mode 0600)."""
import argparse, json, os, stat, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from setup_state_guard import require_state_choice  # noqa: E402
from schedule_config import normalize_timezone, parse_slots, parse_working_hours, persist_schedule  # noqa: E402

HOME = os.path.expanduser("~")
ROOT = os.environ.get("SLACK_DIGEST_HOME") or os.path.join(HOME, ".slack-daily-digest")
CRED_PATH = os.path.join(ROOT, "credentials.json")
ROUTINE_PATH = os.path.join(ROOT, "routine.json")


def load():
    if os.path.exists(CRED_PATH):
        with open(CRED_PATH) as f:
            return json.load(f)
    return {}


def save(data):
    os.makedirs(ROOT, exist_ok=True)
    tmp = CRED_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(tmp, CRED_PATH)
    print(f"OK: credentials saved to {CRED_PATH} (mode 0600)")


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slack-token")
    ap.add_argument("--lark-app-id")
    ap.add_argument("--lark-app-secret")
    ap.add_argument("--lark-user-email")
    ap.add_argument("--lark-chat-id")
    ap.add_argument("--lark-folder-token")
    ap.add_argument("--lark-doc-token")
    ap.add_argument("--lark-target")
    ap.add_argument("--slack-channel", action="append",
                    help="optional Slack channel ID/name limiter; repeatable")
    ap.add_argument("--reschedule", help="comma-separated HH:MM e.g. '11:00,16:00'")
    ap.add_argument("--timezone", default="Asia/Shanghai", help="IANA timezone for local routine")
    ap.add_argument("--working-hours", default="08:00-19:00", help="HH:MM-HH:MM local working window")
    args = ap.parse_args()

    if not require_state_choice():
        return 2

    data = load()
    if args.slack_token:
        data["slack_user_token"] = args.slack_token
    if args.lark_app_id:
        data["lark_app_id"] = args.lark_app_id
    if args.lark_app_secret:
        data["lark_app_secret"] = args.lark_app_secret
    if args.lark_user_email:
        data["lark_user_email"] = args.lark_user_email
    if args.lark_chat_id:
        data["lark_chat_id"] = args.lark_chat_id
    if args.lark_folder_token:
        data["lark_folder_token"] = args.lark_folder_token
    if args.lark_doc_token:
        data["lark_doc_token"] = args.lark_doc_token
    if args.lark_target:
        data["lark_target"] = args.lark_target
    if args.slack_channel:
        data["slack_channels"] = args.slack_channel

    if args.reschedule:
        slots = parse_slots(args.reschedule)
        timezone = normalize_timezone(args.timezone)
        working_hours = parse_working_hours(args.working_hours) if args.working_hours else None
        index, routine = persist_schedule(ROOT, slots, timezone, working_hours)
        print(f"OK: schedule updated -> slots={routine['slots']} timezone={routine['timezone']} working_hours={routine.get('working_hours')}")

    if any([
        args.slack_token,
        args.lark_app_id,
        args.lark_app_secret,
        args.lark_user_email,
        args.lark_chat_id,
        args.lark_folder_token,
        args.lark_doc_token,
        args.lark_target,
        args.slack_channel,
    ]):
        save(data)


if __name__ == "__main__":
    sys.exit(main())
