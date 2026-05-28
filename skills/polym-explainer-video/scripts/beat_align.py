#!/usr/bin/env python3
"""
Beat-sync — snap segment transitions to music onsets (PR #10).

After Volcengine music is generated (Phase 4 step 4), extract the onset
envelope and snap every segment's `transition_in` time + every internal
beat marked `snap_to_beat: true` to the nearest detected onset (within
±150ms by default).

This makes content changes feel rhythmically connected to the music
instead of arbitrary. The OpenAI/Apple grammar of "visual events on
the beat" is what makes those launch videos feel intentional.

Usage:
    python3 beat_align.py storyboard.json assets/music_bed.m4a \\
        --tolerance 0.15 \\
        --out storyboard.beat-aligned.json

Requires:
    pip install librosa numpy soundfile

Falls back gracefully if librosa is not installed (no-op + warning).
"""
import argparse
import json
import sys
from pathlib import Path


def detect_onsets(audio_path: Path):
    """Return list of onset timestamps (seconds) using librosa.

    If librosa isn't available, returns None. Caller should treat that
    as "skip beat-alignment for this run".
    """
    try:
        import librosa
        import numpy as np
    except ImportError:
        return None
    y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units="frames")
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    return list(onset_times)


def snap_to_nearest(t: float, onsets: list, tolerance: float) -> float:
    if not onsets:
        return t
    nearest = min(onsets, key=lambda o: abs(o - t))
    if abs(nearest - t) <= tolerance:
        return float(nearest)
    return t


def align(storyboard: dict, onsets: list, tolerance: float) -> dict:
    changes = []
    for seg in storyboard["segments"]:
        if not seg.get("snap_to_beat", False):
            # default-snap transition_in even if snap_to_beat isn't set
            if seg.get("transition_in") in (None, "", "cut"):
                continue
        original_start = seg["start"]
        snapped = snap_to_nearest(original_start, onsets, tolerance)
        if snapped != original_start:
            delta = snapped - original_start
            changes.append(
                {
                    "id": seg["id"],
                    "field": "start",
                    "original": original_start,
                    "snapped": snapped,
                    "delta": delta,
                }
            )
            seg["start"] = snapped
        # internal beats
        for beat in seg.get("beats", []):
            if not beat.get("snap_to_beat", seg.get("snap_to_beat", False)):
                continue
            orig = beat.get("at", seg["start"])
            sn = snap_to_nearest(orig, onsets, tolerance)
            if sn != orig:
                changes.append(
                    {
                        "id": f"{seg['id']}.{beat.get('name', '?')}",
                        "field": "beat.at",
                        "original": orig,
                        "snapped": sn,
                        "delta": sn - orig,
                    }
                )
                beat["at"] = sn
    storyboard.setdefault("_beat_align", {})["changes"] = changes
    storyboard["_beat_align"]["onsets_detected"] = len(onsets) if onsets else 0
    return storyboard


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard", type=Path)
    ap.add_argument("audio", type=Path)
    ap.add_argument(
        "--tolerance",
        type=float,
        default=0.15,
        help="Max seconds to snap a transition to an onset (default 0.15 = 150ms)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        help="Output path (default: <storyboard>.beat-aligned.json)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print changes but don't write the output file",
    )
    args = ap.parse_args()
    if not args.storyboard.exists():
        print(f"error: {args.storyboard} not found", file=sys.stderr)
        sys.exit(2)
    if not args.audio.exists():
        print(f"error: {args.audio} not found", file=sys.stderr)
        sys.exit(2)

    onsets = detect_onsets(args.audio)
    if onsets is None:
        print(
            "WARN: librosa not installed; install with `pip install --user librosa "
            "numpy soundfile` to enable beat-sync. Skipping for this run.",
            file=sys.stderr,
        )
        sys.exit(0)
    print(f"Detected {len(onsets)} onset(s) in {args.audio.name}", file=sys.stderr)

    sb = json.loads(args.storyboard.read_text())
    sb = align(sb, onsets, args.tolerance)
    changes = sb["_beat_align"]["changes"]
    if not changes:
        print("No changes — every transition already on (or far from) an onset.")
        return 0
    print(f"Snapped {len(changes)} timing(s):")
    for c in changes:
        sign = "+" if c["delta"] >= 0 else ""
        print(
            f"  · {c['id']:<30} {c['field']:<10} "
            f"{c['original']:.3f} → {c['snapped']:.3f}  ({sign}{c['delta']:+.3f}s)"
        )
    if args.dry_run:
        return 0
    out = args.out or args.storyboard.with_suffix(".beat-aligned.json")
    out.write_text(json.dumps(sb, indent=2))
    print(f"\n✓ wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
