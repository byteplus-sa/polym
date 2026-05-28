#!/usr/bin/env python3
"""Local Lark publishing for an already synthesized final digest.

The core publish pipeline (fence-strip → doc → index → IM notify) now lives
in digest_publish.publish_final_digest().  This module keeps the legacy
publish() / write_result() / PublishError API so existing callers continue
to work, but all new code should call publish_final_digest() directly.
"""
import json
import os
import stat

from lark_doc_client import get_lark_doc_client
from status_renderer import render_status

HOME = os.path.expanduser("~")
ROOT = os.environ.get("SLACK_DIGEST_HOME") or os.path.join(HOME, ".slack-daily-digest")
INDEX_PATH = os.path.join(ROOT, "index.json")


class PublishError(RuntimeError):
    def __init__(self, message, index_url=None, digest_url=None):
        super().__init__(message)
        self.index_url = index_url
        self.digest_url = digest_url


def load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    with open(path) as f:
        return json.load(f)


def save_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(tmp, path)


def resolve_runtime_path(path):
    if os.path.isabs(path):
        return path
    return os.path.join(ROOT, path)


def publish(markdown_path, date, slot="", timezone="UTC"):
    """Legacy entry point kept for backward compatibility.

    Delegates to digest_publish.publish_final_digest() which handles
    Bug 1 (fence strip), Bug 2 (newest-on-top index), Bug 3 (IM notify).
    """
    from digest_publish import publish_final_digest  # noqa

    markdown_path = resolve_runtime_path(markdown_path)
    result = publish_final_digest(date=date, slot=slot, markdown_path=markdown_path, timezone=timezone)
    index_url = result.get("index_url")
    doc_url = result.get("doc_url")
    render_status("digest report created and added to index", index_url=index_url, digest_url=doc_url)
    return {"index_url": index_url, "digest_url": doc_url}


def write_result(date, slot, payload):
    result_path = os.path.join(ROOT, "runs", date, f"result_{slot}.json")
    save_json(result_path, payload)
