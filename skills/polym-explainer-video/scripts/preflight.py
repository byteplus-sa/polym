#!/usr/bin/env python3
"""
Pre-flight check for the explainer-video skill.

Verifies local tools, CLIs, and the onboarding config required by the
5-phase workflow. Credentials live in ~/.explainer-video/config.json
(written by the onboarding flow), NOT in environment variables.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def check(label, ok, hint=""):
    mark = "✓" if ok else "✗"
    line = f"  {mark} {label}"
    if hint and not ok:
        line += f"\n      → {hint}"
    print(line)
    return ok


def run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, "", ""


print("=" * 60)
print("explainer-video skill — preflight check")
print("=" * 60)

print("\n[1/3] Local tools")

ok_node, node_v, _ = run(["node", "--version"])
node_major = int(node_v.lstrip("v").split(".")[0]) if ok_node and node_v else 0
check("Node.js v22+", ok_node and node_major >= 22,
      "install Node 22+ from https://nodejs.org")

ok_python = shutil.which("python3") is not None
check("Python 3", ok_python, "install Python 3.8+")

ok_ff, ff_out, _ = run(["ffmpeg", "-version"])
check("ffmpeg", ok_ff, "brew install ffmpeg / apt install ffmpeg")

ok_ffprobe = shutil.which("ffprobe") is not None
check("ffprobe", ok_ffprobe, "comes with ffmpeg")

print("\n[2/3] CLIs")

ok_claude = shutil.which("claude") is not None
check("Claude Code CLI", ok_claude, "install from https://docs.claude.com/en/docs/claude-code/overview")

ok_lark = shutil.which("lark-cli") is not None
check("lark-cli (only needed for Lark/Feishu doc input + upload)", ok_lark,
      "npm install -g @larksuite/cli")

print("\n[3/3] Onboarding config")

cfg_path = Path.home() / ".explainer-video" / "config.json"
ok_cfg = cfg_path.exists()
cfg = {}
if ok_cfg:
    try:
        cfg = json.loads(cfg_path.read_text())
    except (json.JSONDecodeError, OSError):
        ok_cfg = False

check(f"config.json present ({cfg_path})", ok_cfg,
      "run the skill — the onboarding flow will create it")

required = ["modelark_api_key", "iam_ak", "iam_sk",
            "portrait_image", "reference_video", "output_folder"]
ok_fields = True
if ok_cfg:
    for field in required:
        present = bool(cfg.get(field))
        ok_fields = ok_fields and present
        check(f"  config.{field}", present, "re-run onboarding to set this")
    # portrait_image and reference_video should point at real files
    for field in ("portrait_image", "reference_video"):
        val = cfg.get(field, "")
        if val:
            exists = Path(os.path.expanduser(val)).exists()
            ok_fields = ok_fields and exists
            check(f"  {field} file exists", exists, f"missing: {val}")
    # AI music is optional — Volcengine keys are required only when it is enabled
    if cfg.get("music_enabled"):
        for field in ("volc_music_ak", "volc_music_sk"):
            present = bool(cfg.get(field))
            ok_fields = ok_fields and present
            check(f"  config.{field} (music enabled)", present,
                  "re-run onboarding, or set music_enabled=false")
    else:
        check("  AI music disabled — Volcengine keys not required", True)

print()
print("=" * 60)

if all([ok_node and node_major >= 22, ok_python, ok_ff, ok_ffprobe,
        ok_cfg, ok_fields]):
    print("All systems ready. Proceed with Phase 1 (intake).")
else:
    print("Some prerequisites are missing. Fix the items marked ✗ above before continuing.")
    sys.exit(1)
