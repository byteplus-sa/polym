#!/usr/bin/env python3
"""Shared Lark helpers: tenant token, email->open_id, doc edit via lark-docs-skill CLI."""
import json, os, subprocess, time, urllib.parse, urllib.request

HOME = os.path.expanduser("~")
ROOT = os.environ.get("SLACK_DIGEST_HOME") or os.path.join(HOME, ".slack-daily-digest")
CRED = os.path.join(ROOT, "credentials.json")
TOKEN_CACHE = os.path.join(ROOT, ".lark_tenant_token")


def load_creds():
    with open(CRED) as f:
        return json.load(f)


def tenant_token():
    """Return a cached tenant_access_token; refresh if missing or older than 90 min."""
    if os.path.exists(TOKEN_CACHE):
        age = time.time() - os.stat(TOKEN_CACHE).st_mtime
        if age < 90 * 60:
            with open(TOKEN_CACHE) as f:
                return f.read().strip()

    creds = load_creds()
    body = json.dumps({"app_id": creds["lark_app_id"], "app_secret": creds["lark_app_secret"]}).encode()
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
    if d.get("code") != 0:
        raise RuntimeError(f"Lark token err: {d}")
    tok = d["tenant_access_token"]
    with open(TOKEN_CACHE, "w") as f:
        f.write(tok)
    return tok


def email_to_open_id(email):
    tok = tenant_token()
    body = json.dumps({"emails": [email]}).encode()
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id?user_id_type=open_id",
        data=body, headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())
    if d.get("code") != 0:
        raise RuntimeError(f"email->open_id err: {d}")
    users = d["data"]["user_list"]
    if not users or not users[0].get("user_id"):
        raise RuntimeError(f"email {email} not found in Lark contact")
    return users[0]["user_id"]


def send_im_card(open_id, card):
    tok = tenant_token()
    body = json.dumps({
        "receive_id": open_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False),
    }).encode()
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
        data=body, headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def doc_edit_inplace(doc_url, edits_path, skill_path):
    """Invoke lark-docs-skill edit-inplace via subprocess. Caller passes the edits JSON file path."""
    cmd = ["python3.11", "-m", "lark_docs", "edit-inplace", doc_url, f"@{edits_path}"]
    return subprocess.run(cmd, cwd=skill_path, capture_output=True, text=True)


def doc_create(title, content_path, skill_path):
    cmd = ["python3.11", "-m", "lark_docs", "create-doc", title, f"@{content_path}"]
    return subprocess.run(cmd, cwd=skill_path, capture_output=True, text=True)


def doc_read(doc_url, skill_path, fmt="text"):
    cmd = ["python3.11", "-m", "lark_docs", "read-doc", doc_url]
    if fmt:
        cmd += ["--output-format", fmt]
    return subprocess.run(cmd, cwd=skill_path, capture_output=True, text=True)
