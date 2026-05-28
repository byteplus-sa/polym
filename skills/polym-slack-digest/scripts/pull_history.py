#!/usr/bin/env python3
"""Pull conversations.history for every channel within [oldest, latest]."""
import argparse, json, os, sys, time, urllib.parse, urllib.request

HOME = os.path.expanduser("~")
ROOT = os.environ.get("SLACK_DIGEST_HOME") or os.path.join(HOME, ".slack-daily-digest")
CRED = os.path.join(ROOT, "credentials.json")


def call(token, ch_id, oldest, latest):
    p = {"channel": ch_id, "oldest": oldest, "latest": latest, "limit": 200}
    qs = urllib.parse.urlencode(p)
    req = urllib.request.Request(f"https://slack.com/api/conversations.history?{qs}",
                                 headers={"Authorization": f"Bearer {token}"})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
                if d.get("ok"):
                    return d
                if d.get("error") == "ratelimited":
                    time.sleep(60)
                    continue
                return d
        except Exception as e:
            print(f"  retry {i+1}: {e}", file=sys.stderr)
            time.sleep(2)
    return {"ok": False, "error": "max_retries"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channels", required=True, help="path to channels.json")
    ap.add_argument("--oldest", required=True)
    ap.add_argument("--latest", required=True)
    ap.add_argument("--output", required=True, help="path to history.json")
    args = ap.parse_args()

    with open(CRED) as f:
        token = json.load(f)["slack_user_token"]
    with open(args.channels) as f:
        channels = json.load(f)

    print(f"OLDEST={args.oldest} LATEST={args.latest} channels={len(channels)}")
    results = {}
    active = 0
    for i, ch in enumerate(channels):
        ch_id = ch["id"]
        ch_name = ch.get("name") or ch.get("user", ch_id)
        if ch.get("is_im"):
            ch_name = f"DM-{ch.get('user', ch_id)}"
        d = call(token, ch_id, args.oldest, args.latest)
        if not d.get("ok"):
            print(f"[{i+1}/{len(channels)}] {ch_name}: ERR {d.get('error')}", file=sys.stderr)
            time.sleep(0.3)
            continue
        msgs = d.get("messages", [])
        real = [m for m in msgs if m.get("subtype") not in
                ("channel_join", "channel_leave", "channel_topic", "channel_purpose")]
        if real:
            results[ch_id] = {
                "name": ch_name,
                "is_im": ch.get("is_im", False),
                "is_mpim": ch.get("is_mpim", False),
                "is_private": ch.get("is_private", False),
                "messages": real,
            }
            active += 1
            print(f"[{i+1}/{len(channels)}] {ch_name}: {len(real)} msgs OK")
        time.sleep(0.3)

    with open(args.output, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print(f"\nActive channels: {active}/{len(channels)}")
    print(f"Total real messages: {sum(len(v['messages']) for v in results.values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
