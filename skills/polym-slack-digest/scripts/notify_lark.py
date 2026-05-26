#!/usr/bin/env python3
"""Send a Lark IM card to the configured user with Highlights + TODO + doc URL."""
import argparse, json, os, sys

HOME = os.path.expanduser("~")
ROOT = os.environ.get("SLACK_DIGEST_HOME") or os.path.join(HOME, ".slack-daily-digest")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lark_helpers import load_creds, email_to_open_id, send_im_card  # noqa


def build_card(title, doc_url, highlights, todos):
    elements = []
    if highlights:
        elements.append({"tag": "div", "text": {"tag": "lark_md",
                                                "content": "**📌 Highlights**\n" + "\n".join(
                                                    f"- {h}" for h in highlights)}})
    if todos:
        elements.append({"tag": "hr"})
        elements.append({"tag": "div", "text": {"tag": "lark_md",
                                                "content": "**✅ TODO**\n" + "\n".join(
                                                    f"- {t}" for t in todos)}})
    elements.append({"tag": "hr"})
    elements.append({
        "tag": "action",
        "actions": [{"tag": "button",
                     "text": {"tag": "plain_text", "content": "Open Full Digest"},
                     "type": "primary",
                     "url": doc_url}],
    })
    return {
        "header": {"title": {"tag": "plain_text", "content": title},
                   "template": "blue"},
        "elements": elements,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-email")
    ap.add_argument("--title", required=True)
    ap.add_argument("--doc-url", required=True)
    ap.add_argument("--highlights-file", help="text file, one highlight per line")
    ap.add_argument("--todos-file", help="text file, one todo per line")
    args = ap.parse_args()

    email = args.user_email or load_creds().get("lark_user_email")
    if not email:
        print("ERR: no user email configured", file=sys.stderr); return 1

    highlights = []
    if args.highlights_file and os.path.exists(args.highlights_file):
        with open(args.highlights_file) as f:
            highlights = [l.strip() for l in f if l.strip()][:5]
    todos = []
    if args.todos_file and os.path.exists(args.todos_file):
        with open(args.todos_file) as f:
            todos = [l.strip() for l in f if l.strip()][:5]

    open_id = email_to_open_id(email)
    card = build_card(args.title, args.doc_url, highlights, todos)
    resp = send_im_card(open_id, card)
    print(json.dumps(resp, ensure_ascii=False))
    return 0 if resp.get("code") == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
