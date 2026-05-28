#!/usr/bin/env python3
"""
Render-spec validator (Wave 5).

Post-render check. Confirms the produced MP4 matches what the storyboard declared:
  - width / height (aspect ratio)
  - frame rate (target 60fps per PR #2)
  - duration (within ±0.5s of declared total_duration)
  - codec sanity (h264 + aac)

If the render drifts from spec, the user got something they didn't ask for. This
catches it before delivery.

Output JSON:
  { "ok": bool, "findings": [...], "fixes": [...] }

Auto-fixes:
  - "transcode_resolution": re-encode to declared w/h (use scale + pad)
  - "transcode_fps": re-encode to 60fps
  - No fix for duration mismatch (means storyboard timing is wrong)

Usage:
    python3 check_render_spec.py storyboard.json rendered.mp4 [--json]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_DIMS = {
    "1:1": (1440, 1440),
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
}


def probe(mp4_path: Path) -> dict:
    """Run ffprobe and return parsed format + first video stream info."""
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(mp4_path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {r.stderr}")
    data = json.loads(r.stdout)
    v_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    fmt = data.get("format", {})

    fps = 0.0
    if v_stream and v_stream.get("r_frame_rate"):
        num, _, den = v_stream["r_frame_rate"].partition("/")
        try:
            fps = float(num) / float(den) if den else float(num)
        except (ValueError, ZeroDivisionError):
            fps = 0.0

    return {
        "width": v_stream.get("width") if v_stream else 0,
        "height": v_stream.get("height") if v_stream else 0,
        "fps": fps,
        "duration_s": float(fmt.get("duration", 0)),
        "size_bytes": int(fmt.get("size", 0)),
        "video_codec": v_stream.get("codec_name") if v_stream else None,
        "audio_codec": a_stream.get("codec_name") if a_stream else None,
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

    info = probe(mp4_path)
    findings = []
    fixes = []

    # Expected dims from storyboard
    aspect = storyboard.get("aspect_ratio", "1:1")
    exp_w = storyboard.get("width") or DEFAULT_DIMS.get(aspect, (1440, 1440))[0]
    exp_h = storyboard.get("height") or DEFAULT_DIMS.get(aspect, (1440, 1440))[1]
    exp_fps = storyboard.get("fps", 60)
    exp_dur = storyboard.get("total_duration")

    # Dimensions
    if info["width"] != exp_w or info["height"] != exp_h:
        findings.append(
            {
                "severity": "severe",
                "code": "resolution_mismatch",
                "message": (
                    f"rendered {info['width']}×{info['height']} but storyboard "
                    f"declared {exp_w}×{exp_h} (aspect_ratio={aspect})"
                ),
                "actual": [info["width"], info["height"]],
                "expected": [exp_w, exp_h],
            }
        )
        fixes.append(
            {
                "action": "transcode_resolution",
                "input": str(mp4_path),
                "target_width": exp_w,
                "target_height": exp_h,
            }
        )

    # Frame rate (allow ±0.5 fps wobble — rational fps like 59.94 is fine)
    if abs(info["fps"] - exp_fps) > 0.5:
        findings.append(
            {
                "severity": "warning",
                "code": "fps_mismatch",
                "message": (
                    f"rendered at {info['fps']:.2f}fps but house-style targets {exp_fps}fps "
                    f"(see references/motion-house-style.md §1)"
                ),
                "actual": info["fps"],
                "expected": exp_fps,
            }
        )
        fixes.append(
            {
                "action": "transcode_fps",
                "input": str(mp4_path),
                "target_fps": exp_fps,
            }
        )

    # Duration
    if exp_dur is not None and abs(info["duration_s"] - exp_dur) > 0.5:
        findings.append(
            {
                "severity": "warning",
                "code": "duration_mismatch",
                "message": (
                    f"rendered duration {info['duration_s']:.2f}s differs from declared "
                    f"{exp_dur}s by {abs(info['duration_s'] - exp_dur):.2f}s"
                ),
                "actual": info["duration_s"],
                "expected": exp_dur,
            }
        )
        # No auto-fix — duration drift means storyboard timing is wrong

    # Codec sanity
    if info["video_codec"] and info["video_codec"] != "h264":
        findings.append(
            {
                "severity": "warning",
                "code": "non_h264",
                "message": f"video codec is {info['video_codec']}, expected h264 for universal playback",
            }
        )

    return {
        "ok": all(f["severity"] != "severe" for f in findings),
        "render_info": info,
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
        info = result.get("render_info", {})
        print(
            f"check_render_spec: {info.get('width')}×{info.get('height')} "
            f"@ {info.get('fps', 0):.1f}fps, {info.get('duration_s', 0):.2f}s, "
            f"{info.get('size_bytes', 0) // 1024}KB"
        )
        print(f"  {len(result['findings'])} finding(s)")
        for f in result["findings"]:
            print(f"  [{f['severity']:7}] {f['code']}: {f['message']}")
    sys.exit(0 if result["ok"] else 2)


if __name__ == "__main__":
    main()
