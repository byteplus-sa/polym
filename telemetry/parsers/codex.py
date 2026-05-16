"""Codex session log parser.

Scans ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl and
~/.codex/archived_sessions/*.jsonl.

Codex emits *cumulative* token totals per session. We turn that into per-API-call
deltas by diffing successive `token_count` events against the previous total
within the same file. Model is taken from the most recent `turn_context` event
before each token_count.

See cc-switch session_usage_codex.rs for the reference logic — including model
name normalization (strip provider/ prefix and date suffixes) which we replicate.

A file's mtime is the only sync state — when it advances we re-read from line
1 and recompute deltas fresh. Dedup keys ((session, event_index)) prevent
double-counting if records overlap across runs.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Iterator

from . import UsageRecord


_ISO_DATE_SUFFIX = re.compile(r"-\d{4}-\d{2}-\d{2}$")
_COMPACT_DATE_SUFFIX = re.compile(r"-\d{8}$")


def codex_dir() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def normalize_model(raw: str) -> str:
    name = raw.lower()
    if "/" in name:
        name = name.rsplit("/", 1)[1]            # openai/gpt-5 -> gpt-5
    name = _ISO_DATE_SUFFIX.sub("", name)         # gpt-5-2026-03-05 -> gpt-5
    name = _COMPACT_DATE_SUFFIX.sub("", name)     # gpt-5-20260305 -> gpt-5
    return name


def collect_files() -> list[Path]:
    root = codex_dir()
    files: list[Path] = []

    sessions = root / "sessions"
    if sessions.is_dir():
        # date-partitioned: sessions/YYYY/MM/DD/*.jsonl
        for year in sessions.iterdir():
            if not year.is_dir():
                continue
            for month in year.iterdir():
                if not month.is_dir():
                    continue
                for day in month.iterdir():
                    if not day.is_dir():
                        continue
                    files.extend(p for p in day.iterdir() if p.suffix == ".jsonl")

    archived = root / "archived_sessions"
    if archived.is_dir():
        files.extend(p for p in archived.iterdir() if p.suffix == ".jsonl")

    return files


def parse_file(path: Path) -> Iterator[UsageRecord]:
    if not path.exists():
        return

    session_id = ""
    current_model = "unknown"
    prev = (0, 0, 0)   # (input, cached_input, output) cumulative
    event_index = 0

    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            rtype = rec.get("type")
            payload = rec.get("payload") or {}

            if rtype == "session_meta":
                sid = payload.get("id")
                if sid:
                    session_id = sid
                continue

            if rtype == "turn_context":
                m = payload.get("model")
                if m:
                    current_model = normalize_model(m)
                continue

            if rtype != "event_msg":
                continue
            if payload.get("type") != "token_count":
                continue

            total = (payload.get("info") or {}).get("total_token_usage") or {}
            cur_input = int(total.get("input_tokens") or 0)
            cur_cached = int(
                total.get("cached_input_tokens")
                if total.get("cached_input_tokens") is not None
                else total.get("cache_read_input_tokens") or 0
            )
            cur_output = int(total.get("output_tokens") or 0)

            d_input = max(cur_input - prev[0], 0)
            d_cached = max(cur_cached - prev[1], 0)
            d_output = max(cur_output - prev[2], 0)
            prev = (cur_input, cur_cached, cur_output)

            if d_input == 0 and d_cached == 0 and d_output == 0:
                continue

            event_index += 1
            yield UsageRecord(
                agent="codex",
                timestamp=rec.get("timestamp", ""),
                session_id=session_id or path.stem,
                model=current_model,
                input_tokens=d_input,
                output_tokens=d_output,
                cache_read_tokens=d_cached,
                cache_creation_tokens=0,
                dedup_id=f"{session_id or path.stem}#{event_index}",
                skills=[],
            )

def parse_all() -> Iterator[UsageRecord]:
    for path in collect_files():
        yield from parse_file(path)
