#!/usr/bin/env python3
"""Resolve user IDs -> names, replace <@Uxxx> mentions, identify per-channel BytePlus owner."""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request
from collections import Counter

HOME = os.path.expanduser("~")
ROOT = os.environ.get("SLACK_DIGEST_HOME") or os.path.join(HOME, ".slack-daily-digest")
CRED = os.path.join(ROOT, "credentials.json")
CACHE = os.path.join(ROOT, "users_cache.json")
OWNER = os.path.join(ROOT, "channel_owner_cache.json")

MENTION_RE = re.compile(r"<@(U[0-9A-Z]+)>")


def load_token():
    with open(CRED) as f:
        return json.load(f)["slack_user_token"]


def load_cache():
    if os.path.exists(CACHE):
        with open(CACHE) as f:
            return json.load(f)
    return {}


def fetch_user(uid, cache, token):
    if uid in cache:
        return cache[uid]
    qs = urllib.parse.urlencode({"user": uid})
    req = urllib.request.Request(f"https://slack.com/api/users.info?{qs}",
                                 headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read())
        if d.get("ok"):
            u = d["user"]
            prof = u.get("profile", {})
            entry = {
                "name": u.get("real_name") or prof.get("real_name") or "",
                "display": prof.get("display_name") or "",
                "title": prof.get("title", ""),
                "email": prof.get("email", ""),
            }
            cache[uid] = entry
            return entry
    except Exception as e:
        print(f"  users.info({uid}) err: {e}", file=sys.stderr)
    return None


def name_of(uid, cache, token):
    u = fetch_user(uid, cache, token)
    if not u:
        return f"User({uid})"
    return u.get("display") or u.get("name") or uid


def resolve_text(text, cache, token):
    if not text:
        return ""
    return MENTION_RE.sub(lambda m: f"@{name_of(m.group(1), cache, token)}", text)


def is_byteplus(user):
    if not user:
        return False
    disp = (user.get("display") or "") + (user.get("name") or "")
    if any(tag in disp for tag in ["(BytePlus)", "(ByteDance)"]):
        return True
    if "@bytedance.com" in (user.get("email") or ""):
        return True
    title = user.get("title") or ""
    if any(kw in title for kw in ["BytePlus", "ByteDance", "Solution",
                                   "Customer Engineer", "Technical Account", "TAM", "SA"]):
        return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--history", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    token = load_token()
    cache = load_cache()
    owner_cache = {}
    if os.path.exists(OWNER):
        with open(OWNER) as f:
            owner_cache = json.load(f)

    with open(args.history) as f:
        history = json.load(f)

    processed = {}
    for ch_id, info in history.items():
        msgs = info["messages"]
        ch_name = info["name"]
        rendered = []
        speakers = Counter()
        bp_speakers = Counter()
        for m in msgs:
            if m.get("user"):
                uid = m["user"]
                user = fetch_user(uid, cache, token)
                speaker = name_of(uid, cache, token)
                speakers[speaker] += 1
                if is_byteplus(user):
                    bp_speakers[speaker] += 1
            elif m.get("bot_id"):
                bp = m.get("bot_profile", {})
                speaker = bp.get("name") or m.get("username") or m["bot_id"]
                speaker = f"[Bot {speaker}]"
                speakers[speaker] += 1
            else:
                speaker = "[unknown]"
            text = resolve_text(m.get("text", ""), cache, token)
            files = m.get("files") or []
            atts = [f"[file:{f.get('name') or f.get('title') or 'file'}]" for f in files]
            for at in (m.get("attachments") or []):
                t = at.get("title") or at.get("fallback") or ""
                link = at.get("title_link") or at.get("from_url") or ""
                if t or link:
                    atts.append(f"[link:{t} {link}]".strip())
            rendered.append({
                "ts": m.get("ts", ""),
                "speaker": speaker,
                "text": text,
                "attachments": atts,
                "thread_ts": m.get("thread_ts"),
                "reply_count": m.get("reply_count", 0),
            })

        primary, fallback = None, []
        if bp_speakers:
            sorted_bp = bp_speakers.most_common()
            primary = sorted_bp[0][0]
            fallback = [s for s, _ in sorted_bp[1:]]
            owner_cache[ch_name] = {
                "primary_owner": primary,
                "fallback_owners": fallback,
                "last_seen": time.strftime("%Y-%m-%d"),
            }
        else:
            oc = owner_cache.get(ch_name) or {}
            primary = oc.get("primary_owner")
            fallback = oc.get("fallback_owners", [])

        processed[ch_id] = {
            "name": ch_name,
            "is_im": info.get("is_im"),
            "is_mpim": info.get("is_mpim"),
            "is_private": info.get("is_private"),
            "msg_count": len(rendered),
            "speakers": dict(speakers),
            "speaker_count": len(speakers),
            "primary_owner": primary,
            "fallback_owners": fallback,
            "messages": list(reversed(rendered)),
        }

    with open(CACHE, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)
    with open(OWNER, "w") as f:
        json.dump(owner_cache, f, ensure_ascii=False, indent=1)
    with open(args.output, "w") as f:
        json.dump(processed, f, ensure_ascii=False, indent=1)

    print(f"Processed {len(processed)} channels")
    for ch_id, p in sorted(processed.items(), key=lambda x: -x[1]["msg_count"]):
        print(f"  #{p['name']}: {p['msg_count']} msgs, {p['speaker_count']} speakers, owner={p['primary_owner']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
