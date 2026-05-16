"""Resolve who's running this CLI: SA name (from lark-cli auth) + machine id."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import uuid


def resolve_sa_name() -> str:
    """Pull display name from lark-cli auth status; fall back to system username."""
    try:
        r = subprocess.run(
            ["lark-cli", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            name = data.get("userName")
            if name:
                return name
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    import getpass
    return getpass.getuser()


def machine_id() -> str:
    """Stable per-machine identifier, hashed so the raw hardware UUID never leaks."""
    raw: str
    if platform.system() == "Darwin":
        try:
            out = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True,
                text=True,
                timeout=3,
            ).stdout
            for line in out.splitlines():
                if "IOPlatformUUID" in line:
                    raw = line.split("=", 1)[1].strip().strip('"')
                    break
            else:
                raw = str(uuid.getnode())
        except Exception:
            raw = str(uuid.getnode())
    else:
        raw = str(uuid.getnode())
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
