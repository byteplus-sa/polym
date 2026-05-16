"""Push aggregated rows to the leaderboard Bitable via lark-cli.

We do batch_create with payload_sha256 computed last so it covers everything
the server will see. Server-side dedup (by sha256) can be added later via a
formula field or a pre-check; for v1 we just record the hash for audit.
"""

from __future__ import annotations

import hashlib
import json
import subprocess

LEADERBOARD_BASE = "UXPdbPJ3kaheZvs2Nc8lLGCcglh"
LEADERBOARD_TABLE = "tblzLWtzKYpysw3M"


def _payload_hash(rows: list[dict]) -> str:
    canonical = json.dumps(rows, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _to_lark_body(rows: list[dict]) -> tuple[dict, str]:
    """Convert to Base v3 batch_create shape: {fields: [names], rows: [[values]]}.

    Returns (body, payload_sha256). All rows share the same sha so server-side
    dedup can drop entire batches that have already landed.
    """
    sha = _payload_hash(rows)
    # Stamp every row with the same payload hash before serialization.
    stamped = [{**row, "payload_sha256": sha} for row in rows]
    # Stable field order across all rows. Use the union; missing keys become None.
    field_names: list[str] = []
    seen = set()
    for row in stamped:
        for key in row:
            if key not in seen:
                seen.add(key)
                field_names.append(key)
    value_rows = [[row.get(name) for name in field_names] for row in stamped]
    return {"fields": field_names, "rows": value_rows}, sha


def upload(rows: list[dict], dry_run: bool = False) -> dict:
    if not rows:
        return {"uploaded": 0, "skipped": 0, "sha256": None}

    body, sha = _to_lark_body(rows)

    if dry_run:
        return {"uploaded": 0, "skipped": len(rows), "sha256": sha, "preview": body}

    cmd = [
        "lark-cli",
        "base",
        "+record-batch-create",
        "--base-token", LEADERBOARD_BASE,
        "--table-id", LEADERBOARD_TABLE,
        "--json", json.dumps(body, ensure_ascii=False),
        "--as", "user",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"lark-cli batch_create failed:\nstdout: {r.stdout}\nstderr: {r.stderr}")
    try:
        resp = json.loads(r.stdout)
    except json.JSONDecodeError:
        resp = {"raw": r.stdout}
    return {"uploaded": len(rows), "skipped": 0, "sha256": sha, "response": resp}
