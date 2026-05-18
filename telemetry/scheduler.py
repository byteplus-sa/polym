"""Register a daily background run on macOS (launchd) or Linux (systemd timer).

Idempotent: re-running `install` replaces the prior schedule. `uninstall` removes
it. We deliberately point launchd at `sys.executable` and the polym repo root
so the user can upgrade Python or move the repo without re-installing — just
re-run `install`.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

LABEL = "io.polym.telemetry"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
CONFIG_DIR = Path.home() / ".config" / "polym" / "telemetry"
LOG_DIR = CONFIG_DIR / "logs"


def _polym_root() -> Path:
    """Path that needs to be on PYTHONPATH for `-m telemetry` to import."""
    # /…/polym/telemetry/scheduler.py → /…/polym  (the repo root)
    return Path(__file__).resolve().parents[1]


def _plist_xml(hour: int, minute: int) -> str:
    python = sys.executable
    root = _polym_root()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>-m</string>
        <string>telemetry</string>
        <string>sync</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{root}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>{root}</string>
    </dict>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>{LOG_DIR / 'sync.out'}</string>
    <key>StandardErrorPath</key>
    <string>{LOG_DIR / 'sync.err'}</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
"""


def _uid() -> str:
    return str(os.getuid())


def install(hour: int = 14, minute: int = 0) -> dict:
    if platform.system() != "Darwin":
        raise RuntimeError(
            "Auto-schedule currently supports macOS only. "
            "On Linux, use a user-level systemd timer or cron entry pointing at "
            "`PYTHONPATH=/path/to/polym python3 -m telemetry sync`."
        )

    # Unload old plist so the new one takes effect without a reboot.
    if PLIST_PATH.exists():
        subprocess.run(
            ["launchctl", "bootout", f"gui/{_uid()}", str(PLIST_PATH)],
            capture_output=True,
        )

    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_text(_plist_xml(hour, minute))

    r = subprocess.run(
        ["launchctl", "bootstrap", f"gui/{_uid()}", str(PLIST_PATH)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(
            f"launchctl bootstrap failed: {r.stderr.strip() or r.stdout.strip()}"
        )

    return {
        "plist": str(PLIST_PATH),
        "next_run": f"{hour:02d}:{minute:02d} local time, daily",
        "logs": str(LOG_DIR),
    }


def uninstall() -> dict:
    if platform.system() != "Darwin":
        raise RuntimeError("Auto-schedule supports macOS only.")
    if not PLIST_PATH.exists():
        return {"removed": False, "reason": "not installed"}
    subprocess.run(
        ["launchctl", "bootout", f"gui/{_uid()}", str(PLIST_PATH)],
        capture_output=True,
    )
    PLIST_PATH.unlink()
    return {"removed": True, "plist": str(PLIST_PATH)}




def status() -> dict:
    out = {"plist": str(PLIST_PATH), "installed": PLIST_PATH.exists()}
    if not out["installed"]:
        return out
    if platform.system() == "Darwin" and shutil.which("launchctl"):
        r = subprocess.run(
            ["launchctl", "print", f"gui/{_uid()}/{LABEL}"],
            capture_output=True,
            text=True,
        )
        out["loaded"] = r.returncode == 0
        # Extract the "next run" line if present.
        for line in (r.stdout or "").splitlines():
            line = line.strip()
            if line.startswith(("state", "last exit code", "next run")):
                out.setdefault("launchctl", []).append(line)
    return out
