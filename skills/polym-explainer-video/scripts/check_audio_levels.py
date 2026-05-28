#!/usr/bin/env python3
"""
Audio level validator (Wave 5).

Post-render check. Confirms:
  - No clipping (max_volume <= -1.0 dBFS headroom)
  - Mean volume in target range for the mode:
      pure-broll (music only) : RMS in [-22, -16] dB  (audible, not blasting)
      hybrid (voice + music)  : overall RMS in [-20, -14] dB; needs sidechain check
      no music                : skip — no audio expected
  - Audio stream exists if music_enabled is true

Output JSON:
  { "ok": bool, "findings": [...], "fixes": [...] }

Auto-fix:
  - "remix_volume": re-mux with adjusted volume gain to bring mean into target
  - No fix for clipping in the source — would need re-generate music

Usage:
    python3 check_audio_levels.py storyboard.json rendered.mp4 [--json]
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Mode-aware target ranges (dB RMS)
TARGET_RANGES = {
    "pure-broll-product-demo": (-22, -16),
    "aroll-broll-hybrid": (-20, -14),
    "aroll-only": (-20, -14),
}
CLIPPING_HEADROOM_DB = -1.0


def probe_volume(mp4_path: Path) -> dict:
    """Run ffmpeg volumedetect; return mean_volume + max_volume in dB."""
    r = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(mp4_path),
            "-af",
            "volumedetect",
            "-vn",
            "-sn",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    text = r.stderr  # ffmpeg writes to stderr
    mean = max_v = None
    m = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", text)
    if m:
        mean = float(m.group(1))
    m = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", text)
    if m:
        max_v = float(m.group(1))
    # Also detect whether audio stream is present
    audio_present = "Audio:" in text or mean is not None
    return {
        "mean_db": mean,
        "max_db": max_v,
        "audio_present": audio_present,
    }


def check(storyboard: dict, mp4_path: Path):
    if not mp4_path.exists():
        return {
            "ok": False,
            "findings": [
                {
                    "severity": "severe",
                    "code": "missing_render",
                    "message": f"rendered MP4 not found: {mp4_path}",
                }
            ],
            "fixes": [],
        }

    # Read music_enabled from skill config — fall back to storyboard hint
    cfg_path = Path.home() / ".explainer-video" / "config.json"
    music_enabled = True
    if cfg_path.exists():
        try:
            music_enabled = json.loads(cfg_path.read_text()).get("music_enabled", True)
        except Exception:
            pass
    music_enabled = storyboard.get("music_enabled", music_enabled)

    findings = []
    fixes = []
    info = probe_volume(mp4_path)

    # Audio present?
    if music_enabled and not info["audio_present"]:
        findings.append(
            {
                "severity": "severe",
                "code": "missing_audio_stream",
                "message": "music_enabled=true but rendered MP4 has no audio stream",
            }
        )
        return {
            "ok": False,
            "audio_info": info,
            "findings": findings,
            "fixes": fixes,
        }
    if not music_enabled and not info["audio_present"]:
        return {
            "ok": True,
            "audio_info": info,
            "findings": [],
            "fixes": [],
        }

    # Clipping
    if info["max_db"] is not None and info["max_db"] > CLIPPING_HEADROOM_DB:
        findings.append(
            {
                "severity": "warning",
                "code": "clipping_risk",
                "message": (
                    f"max_volume={info['max_db']:+.2f} dB exceeds {CLIPPING_HEADROOM_DB} dB headroom; "
                    f"may clip on aggressive playback systems"
                ),
                "max_db": info["max_db"],
            }
        )
        # Auto-fix: pull down by the excess
        excess = info["max_db"] - CLIPPING_HEADROOM_DB
        fixes.append(
            {
                "action": "remix_volume",
                "input": str(mp4_path),
                "gain_db": -excess - 0.5,  # extra safety margin
            }
        )

    # Mean volume in target range?
    mode = storyboard.get("mode", "aroll-broll-hybrid")
    lo, hi = TARGET_RANGES.get(mode, (-20, -14))
    if info["mean_db"] is not None:
        if info["mean_db"] < lo:
            findings.append(
                {
                    "severity": "warning",
                    "code": "audio_too_quiet",
                    "message": (
                        f"mean_volume={info['mean_db']:+.2f} dB below {mode} target "
                        f"[{lo}, {hi}] — viewers will strain to hear"
                    ),
                    "mean_db": info["mean_db"],
                    "target": [lo, hi],
                }
            )
            # Auto-fix: lift by the gap to target midpoint, clipping-safe
            target_mid = (lo + hi) / 2
            gain = target_mid - info["mean_db"]
            # Don't push above clipping headroom
            if info["max_db"] is not None:
                gain = min(gain, CLIPPING_HEADROOM_DB - info["max_db"] - 0.5)
            if gain > 0.5:
                fixes.append(
                    {
                        "action": "remix_volume",
                        "input": str(mp4_path),
                        "gain_db": round(gain, 2),
                    }
                )
        elif info["mean_db"] > hi:
            findings.append(
                {
                    "severity": "warning",
                    "code": "audio_too_loud",
                    "message": (
                        f"mean_volume={info['mean_db']:+.2f} dB above {mode} target "
                        f"[{lo}, {hi}] — overpowering; reduce mix"
                    ),
                    "mean_db": info["mean_db"],
                    "target": [lo, hi],
                }
            )
            target_mid = (lo + hi) / 2
            gain = target_mid - info["mean_db"]
            if gain < -0.5:
                fixes.append(
                    {
                        "action": "remix_volume",
                        "input": str(mp4_path),
                        "gain_db": round(gain, 2),
                    }
                )

    return {
        "ok": all(f["severity"] != "severe" for f in findings),
        "audio_info": info,
        "mode": mode,
        "target_range": [lo, hi],
        "findings": findings,
        "fixes": fixes,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard", type=Path)
    ap.add_argument("mp4", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    sb = json.loads(args.storyboard.read_text())
    result = check(sb, args.mp4)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        info = result.get("audio_info", {})
        if info.get("audio_present"):
            print(
                f"check_audio_levels: mean={info.get('mean_db', '?')} dB "
                f"max={info.get('max_db', '?')} dB · target={result.get('target_range', '?')} ({result.get('mode', '?')})"
            )
        else:
            print(f"check_audio_levels: no audio stream (music_enabled={False})")
        print(f"  {len(result['findings'])} finding(s)")
        for f in result["findings"]:
            print(f"  [{f['severity']:7}] {f['code']}: {f['message']}")
    sys.exit(0 if result["ok"] else 2)


if __name__ == "__main__":
    main()
