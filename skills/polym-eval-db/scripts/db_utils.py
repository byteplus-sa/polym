#!/usr/bin/env python3
"""Shared polym-eval-db path resolution and bootstrap helpers."""

from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path

DOWNLOAD_URL = "https://carey.tos-ap-southeast-1.bytepluses.com/xieyongliang/eval/eval.db"
SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB = SKILL_DIR / "eval.db"


def default_db_path() -> Path:
    """Return the default eval DB path, without downloading it."""
    env_path = os.environ.get("EVAL_DB_PATH")
    if env_path:
        return Path(env_path).expanduser()
    return DEFAULT_DB


def ensure_db(db_path: str | Path | None = None) -> Path:
    """Return an existing DB path, downloading the default eval.db if needed."""
    path = Path(db_path).expanduser() if db_path else default_db_path()
    if path.exists():
        return path

    env_path = os.environ.get("EVAL_DB_PATH")
    explicit_path = db_path is not None or env_path is not None
    if explicit_path and path != DEFAULT_DB:
        sys.exit(f"❌  Database not found: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Database not found: {path}", file=sys.stderr)
    print(f"Downloading eval.db from {DOWNLOAD_URL} ...", file=sys.stderr)
    try:
        urllib.request.urlretrieve(DOWNLOAD_URL, path)
    except Exception as exc:
        sys.exit(f"❌  Failed to download eval.db: {exc}")
    return path
