"""Verify lark-cli has the scopes polym needs.

The set below is deliberately the minimum union of scopes used across the
polym skill pack today (Bitable read/write for the leaderboard + wiki, doc
read/write, IM send/read, calendar/minutes/VC for the meeting skills, contact
search). Adding a skill that needs more should grow this set, then the next
install.sh run will surface the gap.
"""

from __future__ import annotations

import json
import subprocess

REQUIRED_SCOPES: frozenset[str] = frozenset({
    # Bitable — leaderboard, wiki write_queue, knowledge_index
    "base:record:create", "base:record:read", "base:record:update",
    "base:table:read", "base:field:read",
    # Wiki
    "wiki:wiki:readonly", "wiki:node:read", "wiki:node:retrieve",
    # Docs (read for ingest; write for leaderboard weekly summary)
    "docx:document:create", "docx:document:write_only",
    "docs:document.content:read",
    # IM (im-digest, polym-help bot DMs)
    "im:message", "im:message:readonly",
    "im:message.group_msg:get_as_user", "im:message.p2p_msg:get_as_user",
    "im:chat:read",
    # Meetings (meeting-summary, meeting-recorder)
    "minutes:minutes:readonly", "minutes:minutes.artifacts:read",
    "vc:meeting.search:read", "vc:note:read",
    # Contacts (lark-contact name → open_id)
    "contact:user:search", "contact:user.base:readonly",
})


def check() -> tuple[str, set[str], dict]:
    """Return (status, missing_scopes, raw_status_payload).

    status ∈ {"ok", "partial", "expired", "not_logged_in", "error"}.
    """
    try:
        r = subprocess.run(
            ["lark-cli", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return "error", set(REQUIRED_SCOPES), {"error": str(e)}

    if r.returncode != 0 or not r.stdout.strip():
        return "not_logged_in", set(REQUIRED_SCOPES), {"stderr": r.stderr}

    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError as e:
        return "error", set(REQUIRED_SCOPES), {"error": str(e), "raw": r.stdout[:500]}

    if data.get("tokenStatus") != "valid":
        return "expired", set(REQUIRED_SCOPES), data

    granted = set((data.get("scope") or "").split())
    missing = set(REQUIRED_SCOPES) - granted
    return ("ok" if not missing else "partial"), missing, data
