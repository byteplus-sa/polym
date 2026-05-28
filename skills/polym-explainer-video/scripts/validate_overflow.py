#!/usr/bin/env python3
"""Post-render overflow validator.

Detects content that bleeds off the canvas edges during zoom/transform phases.
Hyperframes' built-in `inspect` checks layout against container boxes, but
when a parent uses CSS transform: scale (camera zoom), children can extend
beyond the canvas viewport even though their bounding boxes are correct.

This sampler frames the rendered MP4 at suspicious timestamps and checks
whether any non-background pixels touch the canvas edges within a guard band.

Usage:
    python3 validate_overflow.py <rendered.mp4> [--at 14,17,20,23,26]
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("error: PIL not installed. Run: pip install --user Pillow", file=sys.stderr)
    sys.exit(2)


def extract_frame(mp4_path: Path, ts: float, out_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{ts:.3f}",
            "-i",
            str(mp4_path),
            "-vframes",
            "1",
            str(out_path),
        ],
        check=True,
        capture_output=True,
    )


def edge_has_content(img: Image.Image, edge: str, guard: int, threshold: int) -> int:
    """Return the max distance into the canvas (within guard) at which non-bg
    pixels appear on the named edge. 0 = no content within the guard band."""
    w, h = img.size
    px = img.load()
    bg_samples = [px[w // 2, 4], px[w // 2, h - 4], px[4, h // 2], px[w - 4, h // 2]]
    # Background reference: take the most extreme luminance from the 4 mid-edge
    # samples. We're looking for content that contrasts STRONGLY against the
    # outermost edge, not subtle gradient drift.
    bg_lums = [0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] for c in bg_samples]
    bg_lum = sum(bg_lums) / len(bg_lums)

    worst = 0
    if edge == "left":
        for x in range(guard):
            for y in range(0, h, 8):
                p = px[x, y]
                lum = 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]
                if abs(lum - bg_lum) > threshold:
                    worst = max(worst, guard - x)
                    break
    elif edge == "right":
        for x in range(w - 1, w - 1 - guard, -1):
            for y in range(0, h, 8):
                p = px[x, y]
                lum = 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]
                if abs(lum - bg_lum) > threshold:
                    worst = max(worst, guard - (w - 1 - x))
                    break
    elif edge == "top":
        for y in range(guard):
            for x in range(0, w, 8):
                p = px[x, y]
                lum = 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]
                if abs(lum - bg_lum) > threshold:
                    worst = max(worst, guard - y)
                    break
    elif edge == "bottom":
        for y in range(h - 1, h - 1 - guard, -1):
            for x in range(0, w, 8):
                p = px[x, y]
                lum = 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]
                if abs(lum - bg_lum) > threshold:
                    worst = max(worst, guard - (h - 1 - y))
                    break
    return worst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mp4", type=Path)
    ap.add_argument(
        "--at",
        default="14,17,20,23,26",
        help="comma-separated timestamps (seconds) to sample",
    )
    ap.add_argument("--guard", type=int, default=8, help="edge guard band in px")
    ap.add_argument(
        "--threshold",
        type=int,
        default=70,
        help="luminance delta vs bg that counts as content (0-255)",
    )
    args = ap.parse_args()
    if not args.mp4.exists():
        print(f"error: {args.mp4} not found", file=sys.stderr)
        sys.exit(2)
    timestamps = [float(t) for t in args.at.split(",")]
    findings = []
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for ts in timestamps:
            frame_path = td / f"f_{ts:.2f}.png"
            extract_frame(args.mp4, ts, frame_path)
            img = Image.open(frame_path).convert("RGB")
            for edge in ("left", "right", "top", "bottom"):
                d = edge_has_content(img, edge, args.guard, args.threshold)
                if d > 0:
                    findings.append((ts, edge, d))
    if not findings:
        print(f"OK · {len(timestamps)} samples · no content within {args.guard}px of any edge")
        return 0
    print(f"FAIL · {len(findings)} edge intrusions:")
    for ts, edge, d in findings:
        print(f"  t={ts:>5.2f}s  {edge:<6}  content within {d}px of edge")
    return 1


if __name__ == "__main__":
    sys.exit(main())
