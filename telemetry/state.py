"""Per-file mtime tracking — purely an optimization to skip files that haven't
changed since the last successful sync.

Important: we deliberately do NOT track within-file offsets. Each time a file's
mtime advances we re-read it from line 1. Reason: a single JSONL file commonly
spans multiple local days, and the 14:00 push needs to include any tail tokens
written after yesterday's sync run. Re-reading is cheap (~ms per MB) and our
per-message dedup keys (message.id for cc, session+event_index for codex) make
double-counting impossible.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict, fields
from pathlib import Path


STATE_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "polymath" / "telemetry"
STATE_FILE = STATE_DIR / "sync_state.json"


@dataclass
class FileState:
    mtime_ns: int = 0


@dataclass
class SyncState:
    cc_files: dict[str, FileState] = field(default_factory=dict)
    codex_files: dict[str, FileState] = field(default_factory=dict)

    def cc(self, path: str) -> FileState:
        return self.cc_files.setdefault(path, FileState())

    def codex(self, path: str) -> FileState:
        return self.codex_files.setdefault(path, FileState())


_FIELDSTATE_FIELDS = {f.name for f in fields(FileState)}


def _filestate(v: dict) -> FileState:
    """Forward-compat constructor: silently drop unknown keys so older state
    files (which carried line_offset / prev_total fields we no longer track)
    still load."""
    return FileState(**{k: v[k] for k in v.keys() & _FIELDSTATE_FIELDS})


def load() -> SyncState:
    if not STATE_FILE.exists():
        return SyncState()
    try:
        raw = json.loads(STATE_FILE.read_text())
    except json.JSONDecodeError:
        return SyncState()
    return SyncState(
        cc_files={k: _filestate(v) for k, v in raw.get("cc_files", {}).items()},
        codex_files={k: _filestate(v) for k, v in raw.get("codex_files", {}).items()},
    )


def save(state: SyncState) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(
            {
                "cc_files": {k: asdict(v) for k, v in state.cc_files.items()},
                "codex_files": {k: asdict(v) for k, v in state.codex_files.items()},
            },
            indent=2,
        )
    )
