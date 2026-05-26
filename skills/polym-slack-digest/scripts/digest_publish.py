#!/usr/bin/env python3
"""Shared publish pipeline: strip fence → Lark doc → index (newest-on-top) → IM notify.

Both run_digest.py --publish-existing and local_routine.py run-due must call
publish_final_digest() from this module so both paths go through the same code.
"""
import json
import os
import re
import stat

HOME = os.path.expanduser("~")
ROOT = os.environ.get("SLACK_DIGEST_HOME") or os.path.join(HOME, ".slack-daily-digest")
INDEX_PATH = os.path.join(ROOT, "index.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    with open(path) as f:
        return json.load(f)


def _save_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Bug 1 — Strip outer markdown fence
# ---------------------------------------------------------------------------

def strip_outer_fence(content: str) -> str:
    """Remove a single outer ```markdown ... ``` or ``` ... ``` wrapper.

    Only removes the outermost fence if the very first non-empty line is a
    fence opener and the very last non-empty line is the matching closer.
    Inner fenced code blocks that are part of the content are left untouched.
    """
    stripped = content.strip()
    # Match opening fence: ```markdown or ``` (with optional language tag)
    m = re.match(r"^```[a-zA-Z]*\n(.*)\n```\s*$", stripped, re.DOTALL)
    if m:
        return m.group(1)
    return content


def strip_fence_file(markdown_path: str) -> str:
    """Read file, strip outer fence, write back, return cleaned content."""
    with open(markdown_path, encoding="utf-8") as f:
        content = f.read()
    cleaned = strip_outer_fence(content)
    if cleaned != content:
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(cleaned)
    return cleaned


# ---------------------------------------------------------------------------
# Bug 2 — Index update newest-on-top with de-duplication
# ---------------------------------------------------------------------------

def _entry_line(date: str, slot: str, doc_url: str, doc_token: str) -> str:
    """Return the bullet line to insert into the index."""
    if slot:
        return f"- **{date} {slot}** — [Slack Daily Digest · {date}]({doc_url})"
    return f"- **{date}** — [Slack Daily Digest · {date}]({doc_url})"


def update_index_newest_on_top(client, index_url: str, date: str, slot: str, doc_url: str):
    """Insert a new index entry above the current newest bullet (newest-on-top).

    De-duplicates by date+slot+doc_url before inserting.
    Falls back to append-after-header if no existing bullets found.
    """
    if not index_url:
        return

    # Read the current index doc content
    try:
        raw = client.read_doc(index_url, output_format="markdown")
    except Exception:
        raw = ""

    # Parse content from JSON if the client returns JSON
    content = raw
    if raw.strip().startswith("{"):
        try:
            data = json.loads(raw)
            content = data.get("content") or data.get("markdown") or raw
        except Exception:
            pass

    # Extract doc_token from doc_url for de-dup
    doc_token_match = re.search(r"/(?:docx|docs|doc)/([A-Za-z0-9_-]+)", doc_url)
    doc_token = doc_token_match.group(1) if doc_token_match else doc_url

    # De-duplicate: skip if an entry for same date+slot+doc_token already exists
    dup_pattern = re.compile(
        re.escape(date) + (r"\s+" + re.escape(slot) if slot else r"") + r".*" + re.escape(doc_token),
        re.IGNORECASE,
    )
    # Also check just the doc_url in case it appears literally
    if doc_token in content or (slot and dup_pattern.search(content)):
        return  # already indexed

    entry_line = _entry_line(date, slot, doc_url, doc_token)
    new_bullet = f"\n{entry_line}\n"

    run_dir = os.path.join(ROOT, "runs", date)
    os.makedirs(run_dir, exist_ok=True)
    edits_path = os.path.join(run_dir, "index_update.json")

    # Find the first existing "- **YYYY-MM-DD" bullet to insert before it
    first_bullet_match = re.search(r"^- \*\*\d{4}-\d{2}-\d{2}", content, re.MULTILINE)

    if first_bullet_match:
        # insert_before the current first (newest) entry
        selection = first_bullet_match.group(0)  # e.g. "- **2026-05-22"
        edit = {
            "mode": "insert_before",
            "selection_with_ellipsis": selection + "...",
            "markdown": new_bullet,
        }
    else:
        # No existing bullets — fall back to append after header
        edit = {
            "mode": "append",
            "markdown": new_bullet,
        }

    _save_json(edits_path, edit)
    client.edit_doc(index_url, edits_path)


# ---------------------------------------------------------------------------
# Bug 3 — IM card notification
# ---------------------------------------------------------------------------

def _extract_digest_stats(markdown_path: str):
    """Best-effort extraction of active_channels and effective_messages from the digest."""
    try:
        with open(markdown_path, encoding="utf-8") as f:
            body = f.read()
        channels = 0
        messages = 0
        m = re.search(r"Active channels[:\s]+(\d+)", body, re.IGNORECASE)
        if m:
            channels = int(m.group(1))
        m = re.search(r"(?:Total|Effective)\s+messages[:\s]+(\d+)", body, re.IGNORECASE)
        if m:
            messages = int(m.group(1))
        return channels, messages
    except Exception:
        return 0, 0


def notify_lark_im(date: str, slot: str, timezone: str, doc_url: str,
                   index_url: str, markdown_path: str) -> str:
    """Send an IM card to the configured Lark user.

    Returns a notification_status string:
      "success", "failed:<reason>", or "skipped_missing_target"
    Never raises — errors are captured and returned as status strings.
    """
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from lark_helpers import load_creds, email_to_open_id, send_im_card  # noqa
    except Exception as exc:
        return f"failed:import_error:{exc}"

    try:
        creds = load_creds()
    except Exception as exc:
        return f"failed:creds_load:{exc}"

    email = creds.get("lark_user_email") or creds.get("user_email")
    if not email:
        return "skipped_missing_target"

    active_channels, effective_messages = _extract_digest_stats(markdown_path)

    elements = []
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": (
                f"**Date:** {date}  \n"
                f"**Slot:** {slot}  \n"
                f"**Timezone:** {timezone}  \n"
                f"**Active channels:** {active_channels}  \n"
                f"**Effective messages:** {effective_messages}  \n"
                f"**Status:** success"
            ),
        },
    })
    if index_url:
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "Open Full Digest"},
                    "type": "primary",
                    "url": doc_url,
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "Open Index"},
                    "type": "default",
                    "url": index_url,
                },
            ],
        })
    else:
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "Open Full Digest"},
                    "type": "primary",
                    "url": doc_url,
                },
            ],
        })

    card = {
        "header": {
            "title": {"tag": "plain_text", "content": "Slack Daily Digest completed"},
            "template": "blue",
        },
        "elements": elements,
    }

    try:
        open_id = email_to_open_id(email)
    except Exception as exc:
        return f"failed:email_to_open_id:{exc}"

    try:
        resp = send_im_card(open_id, card)
        if resp.get("code") == 0:
            return "success"
        return f"failed:lark_api_code_{resp.get('code')}:{resp.get('msg', '')}"
    except Exception as exc:
        return f"failed:send_im_card:{exc}"


# ---------------------------------------------------------------------------
# Unified publish entry point
# ---------------------------------------------------------------------------

def publish_final_digest(date: str, slot: str, markdown_path: str, timezone: str = "UTC") -> dict:
    """Full publish pipeline used by both manual and routine paths.

    1. Strip outer fence from final_*.md
    2. Create Lark doc, move to folder
    3. Update index newest-on-top (with de-dup)
    4. Send IM card
    5. Write result_<slot>.json
    6. Return result dict

    Raises PublishError on doc-creation or move failure.
    Never raises on IM notification failure.
    """
    from local_digest_publish import PublishError  # noqa — keep existing class
    from lark_doc_client import get_lark_doc_client  # noqa

    index = _load_json(INDEX_PATH, {})
    client = get_lark_doc_client()
    index_url = index.get("index_doc_url")

    # --- Bug 1: strip outer fence ---
    strip_fence_file(markdown_path)

    # --- Create Lark doc ---
    try:
        doc_url = client.create_doc(f"Slack Daily Digest · {date}", markdown_path)
    except Exception as exc:
        raise PublishError(str(exc), index_url=index_url) from exc

    # --- Move to folder ---
    if index.get("folder_token"):
        try:
            client.move_doc(doc_url, index["folder_token"])
        except Exception as exc:
            raise PublishError(
                f"digest created but move to folder failed: {exc}",
                index_url=index_url, digest_url=doc_url,
            ) from exc

    # --- Bug 2: update index newest-on-top ---
    if index_url:
        try:
            update_index_newest_on_top(client, index_url, date, slot, doc_url)
        except Exception as exc:
            raise PublishError(
                f"digest created but index update failed: {exc}",
                index_url=index_url, digest_url=doc_url,
            ) from exc

    # --- Bug 3: IM notification (never fatal) ---
    notification_status = notify_lark_im(
        date=date,
        slot=slot,
        timezone=timezone,
        doc_url=doc_url,
        index_url=index_url,
        markdown_path=markdown_path,
    )

    result = {
        "ok": True,
        "digest_link": doc_url,
        "doc_url": doc_url,
        "index_link": index_url,
        "index_url": index_url,
        "notification_status": notification_status,
    }

    # Write result_<slot>.json
    slot_key = slot.replace(":", "")
    result_path = os.path.join(ROOT, "runs", date, f"result_{slot_key}.json")
    _save_json(result_path, result)
    # Also write with original slot as key (backward compat)
    result_path2 = os.path.join(ROOT, "runs", date, f"result_{slot}.json")
    if result_path2 != result_path:
        _save_json(result_path2, result)

    return result
