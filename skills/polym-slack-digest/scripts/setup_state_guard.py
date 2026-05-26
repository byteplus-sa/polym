#!/usr/bin/env python3
"""Guard real local setup state from accidental modification."""
import json
import os
import stat

HOME = os.path.expanduser("~")
ROOT = os.environ.get("SLACK_DIGEST_HOME") or os.path.join(HOME, ".slack-daily-digest")
STATE = os.path.join(ROOT, "setup_state.json")


def load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(tmp, path)


def looks_temporary_home():
    real_home = os.path.realpath(HOME)
    return real_home.startswith("/private/tmp/") or real_home.startswith("/tmp/")


def require_state_choice():
    if os.environ.get("SLACK_DIGEST_HOME") or looks_temporary_home() or not os.path.exists(ROOT):
        return True
    state = load_json(STATE)
    if state.get("real_home_choice") in ("use_existing", "backup_start_clean"):
        return True
    print("real_home_state_choice_required")
    print(f"Existing {ROOT} was found. Choose one before setup modifies it:")
    print("A) use existing config")
    print("B) backup and start clean")
    print("C) use isolated runtime only for this test")
    print("Rerun with one of:")
    print("  python3 scripts/setup_state_guard.py --use-existing")
    print("  python3 scripts/setup_state_guard.py --backup-start-clean")
    print("  SLACK_DIGEST_HOME=/tmp/slack-digest-test ...")
    return False


def main():
    import argparse
    import shutil
    import time

    ap = argparse.ArgumentParser()
    ap.add_argument("--use-existing", action="store_true")
    ap.add_argument("--backup-start-clean", action="store_true")
    args = ap.parse_args()

    if args.use_existing:
        save_json(STATE, {"real_home_choice": "use_existing"})
        print(f"OK: using existing {ROOT} config")
        return 0
    if args.backup_start_clean:
        if os.path.exists(ROOT):
            backup = ROOT + ".backup." + time.strftime("%Y%m%d%H%M%S")
            shutil.move(ROOT, backup)
            os.makedirs(ROOT, exist_ok=True)
            save_json(STATE, {"real_home_choice": "backup_start_clean", "backup": backup})
            print(f"OK: backed up existing config to {backup}")
        else:
            save_json(STATE, {"real_home_choice": "backup_start_clean"})
            print("OK: no existing config to back up")
        return 0
    return 0 if require_state_choice() else 2


if __name__ == "__main__":
    raise SystemExit(main())
