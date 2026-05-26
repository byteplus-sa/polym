#!/usr/bin/env python3
"""Refresh users_cache.json via Slack users.list (Tier 2). Skip if cache <7 days old."""
import json, os, sys, time, urllib.parse, urllib.request

HOME = os.path.expanduser("~")
ROOT = os.environ.get("SLACK_DIGEST_HOME") or os.path.join(HOME, ".slack-daily-digest")
CACHE = os.path.join(ROOT, "users_cache.json")
CRED = os.path.join(ROOT, "credentials.json")

MAX_AGE_DAYS = 7


def needs_refresh():
    if not os.path.exists(CACHE):
        return True
    age = (time.time() - os.stat(CACHE).st_mtime) / 86400
    return age >= MAX_AGE_DAYS


def call(token, cursor=""):
    p = {"limit": 200}
    if cursor:
        p["cursor"] = cursor
    qs = urllib.parse.urlencode(p)
    req = urllib.request.Request(f"https://slack.com/api/users.list?{qs}",
                                 headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    force = "--force" in sys.argv
    if not force and not needs_refresh():
        age = (time.time() - os.stat(CACHE).st_mtime) / 86400
        print(f"cache fresh ({age:.2f} days old), skip")
        return 0

    with open(CRED) as f:
        token = json.load(f)["slack_user_token"]

    cache = {}
    cursor = ""
    while True:
        d = call(token, cursor)
        if not d.get("ok"):
            err = d.get("error", "")
            if err == "ratelimited":
                time.sleep(60)
                continue
            print(f"ERR: {err}", file=sys.stderr)
            return 1
        for u in d.get("members", []):
            uid = u["id"]
            prof = u.get("profile", {})
            cache[uid] = {
                "name": u.get("real_name") or prof.get("real_name") or "",
                "display": prof.get("display_name") or "",
                "title": prof.get("title", ""),
                "email": prof.get("email", ""),
            }
        cursor = d.get("response_metadata", {}).get("next_cursor", "")
        if not cursor:
            break
        time.sleep(1)  # Tier 2

    os.makedirs(ROOT, exist_ok=True)
    with open(CACHE, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)
    print(f"OK: cached {len(cache)} users")
    return 0


if __name__ == "__main__":
    sys.exit(main())
