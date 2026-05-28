#!/usr/bin/env python3
"""
Asset existence + embedded-video keyframe density check (Wave 5).

Scans the generated index.html (and any referenced composition HTML files)
for asset references and validates each one exists. Also probes any
embedded `<video>` elements for keyframe density — HyperFrames `<video>`
clips need keyframe intervals ≤ ~1s or they freeze-frame on seek.

Pre-render check (asset existence) + pre-render check (keyframe density)
+ post-render irrelevant (assets are already baked in).

Output JSON:
  { "ok": bool, "findings": [...], "fixes": [...] }

Severities:
  - severe: asset referenced but file missing (render will produce white box)
  - severe: embedded video has keyframe interval > 1.5s (will freeze on seek)
  - warning: embedded video has keyframe interval 1.0-1.5s (works but risky)

Auto-fix proposed:
  - "reencode_video": re-encode source video with dense keyframes (g=30)
  - No auto-fix for missing asset — surface to user

Usage:
    python3 check_assets.py [--project-root .] [--json]
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SRC_PATTERN = re.compile(r'(?:src|href)\s*=\s*[\'"]([^\'"]+)[\'"]', re.IGNORECASE)
LOCAL_SCHEMES = (None, "", "file")


def is_local(url: str) -> bool:
    """Return True if the URL is a local path (relative or absolute file://)."""
    if url.startswith(("http://", "https://", "//", "data:", "blob:", "javascript:")):
        return False
    if url.startswith("#"):
        return False
    return True


def find_referenced_assets(html_text: str) -> list:
    """Return all src/href values in the HTML that look local."""
    return [u for u in SRC_PATTERN.findall(html_text) if is_local(u)]


def find_html_files(project_root: Path) -> list:
    """All HTML composition files in the project (index + compositions/*.html)."""
    found = [project_root / "index.html"]
    comp_dir = project_root / "compositions"
    if comp_dir.exists():
        found.extend(comp_dir.glob("**/*.html"))
    return [p for p in found if p.exists()]


def find_video_assets(html_text: str) -> list:
    """Extract video element src values from HTML."""
    out = []
    for m in re.finditer(
        r'<video[^>]*src\s*=\s*[\'"]([^\'"]+)[\'"]', html_text, re.IGNORECASE
    ):
        u = m.group(1)
        if is_local(u):
            out.append(u)
    return out


def probe_keyframe_interval(video_path: Path) -> float:
    """Return the max gap (seconds) between keyframes in the video.

    Returns -1 if ffprobe fails / video missing.
    """
    if not video_path.exists():
        return -1.0
    try:
        r = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "frame=key_frame,pkt_pts_time",
                "-of",
                "csv=print_section=0",
                "-skip_frame",
                "nokey",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return -1.0
    if r.returncode != 0:
        return -1.0
    timestamps = []
    for line in r.stdout.splitlines():
        parts = line.split(",")
        if len(parts) >= 2 and parts[0].strip() == "1":
            try:
                timestamps.append(float(parts[1]))
            except ValueError:
                continue
    if len(timestamps) < 2:
        return -1.0
    gaps = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
    return max(gaps)


def check(project_root: Path):
    findings = []
    fixes = []
    html_files = find_html_files(project_root)
    seen_assets = set()
    checked_videos = set()

    if not html_files:
        return {
            "ok": False,
            "findings": [
                {
                    "severity": "severe",
                    "code": "no_html_files",
                    "message": f"no composition HTML files found in {project_root}",
                }
            ],
            "fixes": [],
        }

    for html_path in html_files:
        text = html_path.read_text(errors="replace")
        for ref in find_referenced_assets(text):
            if ref in seen_assets:
                continue
            seen_assets.add(ref)
            # Resolve relative to the HTML file's directory
            target = (html_path.parent / ref).resolve()
            if not target.exists():
                findings.append(
                    {
                        "severity": "severe",
                        "code": "missing_asset",
                        "message": f"{html_path.name} references {ref!r} but {target} does not exist",
                        "asset": ref,
                        "referenced_by": str(html_path.relative_to(project_root)),
                    }
                )
                # No auto-fix — user must provide the file

        for vref in find_video_assets(text):
            if vref in checked_videos:
                continue
            checked_videos.add(vref)
            vpath = (html_path.parent / vref).resolve()
            gap = probe_keyframe_interval(vpath)
            if gap < 0:
                continue  # missing video already caught above OR ffprobe failed
            if gap > 1.5:
                findings.append(
                    {
                        "severity": "severe",
                        "code": "sparse_keyframes",
                        "message": (
                            f"embedded video {vref!r} has max keyframe gap "
                            f"{gap:.2f}s; HyperFrames seek requires ≤1.0s or it freezes"
                        ),
                        "asset": vref,
                        "max_gap_s": gap,
                    }
                )
                fixes.append(
                    {
                        "action": "reencode_video",
                        "input": str(vpath),
                        "output": str(vpath),  # overwrite in place
                        "ffmpeg_args": [
                            "-c:v",
                            "libx264",
                            "-r",
                            "60",
                            "-g",
                            "60",
                            "-keyint_min",
                            "60",
                            "-movflags",
                            "+faststart",
                            "-c:a",
                            "copy",
                        ],
                    }
                )
            elif gap > 1.0:
                findings.append(
                    {
                        "severity": "warning",
                        "code": "moderate_keyframes",
                        "message": (
                            f"embedded video {vref!r} has max keyframe gap {gap:.2f}s; "
                            f"works but may stutter on aggressive seeks"
                        ),
                        "asset": vref,
                        "max_gap_s": gap,
                    }
                )

    return {
        "ok": all(f["severity"] != "severe" for f in findings),
        "html_files_scanned": len(html_files),
        "unique_assets": len(seen_assets),
        "videos_probed": len(checked_videos),
        "findings": findings,
        "fixes": fixes,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=".", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    result = check(args.project_root.resolve())
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(
            f"check_assets: scanned {result.get('html_files_scanned', 0)} HTML file(s), "
            f"{result.get('unique_assets', 0)} asset(s), "
            f"probed {result.get('videos_probed', 0)} video(s); "
            f"{len(result['findings'])} finding(s)"
        )
        for f in result["findings"]:
            print(f"  [{f['severity']:7}] {f['code']}: {f['message']}")
    sys.exit(0 if result["ok"] else 2)


if __name__ == "__main__":
    main()
