#!/usr/bin/env python3
"""List conversations the configured user can access, optionally limited by channel."""
import argparse, json, os, sys, time, urllib.parse, urllib.request

HOME = os.path.expanduser("~")
ROOT = os.environ.get("SLACK_DIGEST_HOME") or os.path.join(HOME, ".slack-daily-digest")
CRED = os.path.join(ROOT, "credentials.json")


def call(token, params):
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"https://slack.com/api/users.conversations?{qs}",
                                 headers={"Authorization": f"Bearer {token}"})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            print(f"retry {i+1}: {e}", file=sys.stderr)
            time.sleep(2)
    return {"ok": False}


def configured_channel_limits(creds, cli_channels):
    raw = []
    raw.extend(cli_channels or [])
    for env_name in ("TEST_SLACK_CHANNEL", "TEST_SLACK_CHANNEL_ID"):
        if os.environ.get(env_name):
            raw.append(os.environ[env_name])
    for key in ("test_slack_channel", "test_slack_channel_id", "slack_channel", "slack_channel_id"):
        if creds.get(key):
            raw.append(creds[key])
    for key in ("slack_channels", "slack_channel_ids"):
        value = creds.get(key)
        if isinstance(value, list):
            raw.extend(value)
        elif value:
            raw.extend(str(value).split(","))
    seen = set()
    limits = []
    for item in raw:
        value = str(item).strip()
        if value.startswith("#"):
            value = value[1:]
        if value and value not in seen:
            seen.add(value)
            limits.append(value)
    return limits


def matches_limit(channel, limits):
    if not limits:
        return True
    names = {
        channel.get("id"),
        channel.get("name"),
        channel.get("user"),
        channel.get("name_normalized"),
    }
    return any(limit in names for limit in limits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_path", nargs="?", default=os.path.join(ROOT, "channels.json"))
    ap.add_argument("--channel", action="append", default=[],
                    help="optional Slack channel ID/name limiter; repeatable")
    args = ap.parse_args()

    creds = {}
    if os.path.exists(CRED):
        with open(CRED) as f:
            creds = json.load(f)
    if os.environ.get("SLACK_USER_TOKEN"):
        creds["slack_user_token"] = os.environ["SLACK_USER_TOKEN"]
    token = creds.get("slack_user_token")
    if not token:
        print("ERR: missing_credentials: SLACK_USER_TOKEN", file=sys.stderr)
        return 1
    limits = configured_channel_limits(creds, args.channel)

    all_chs = []
    cursor = ""
    while True:
        p = {"types": "public_channel,private_channel,mpim,im",
             "limit": 200, "exclude_archived": "true"}
        if cursor:
            p["cursor"] = cursor
        d = call(token, p)
        if not d.get("ok"):
            print(f"ERR: {d.get('error')}", file=sys.stderr)
            return 1
        all_chs.extend(d.get("channels", []))
        cursor = d.get("response_metadata", {}).get("next_cursor", "")
        if not cursor:
            break
        time.sleep(0.3)

    if not all_chs:
        print("ERR: no accessible Slack channels could be listed", file=sys.stderr)
        return 1

    selected = [ch for ch in all_chs if matches_limit(ch, limits)]
    if limits and not selected:
        print(f"ERR: configured Slack channel not found or not accessible: {', '.join(limits)}",
              file=sys.stderr)
        return 1

    with open(args.out_path, "w") as f:
        json.dump(selected, f, ensure_ascii=False, indent=1)
    scope = "limited" if limits else "accessible"
    print(f"OK: {len(selected)} {scope} channels -> {args.out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
