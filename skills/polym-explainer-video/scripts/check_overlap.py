#!/usr/bin/env python3
"""
Scene-overlap / z-layer collision check (Wave 5).

Detects two failure modes:
  1. Two clips on the same track with overlapping time windows = same-track collision
  2. Two clips with overlapping time windows that BOTH render visible content,
     without an explicit transition_in on the later clip = likely unintended overlap

Pre-render check. Reads storyboard.json. Output JSON:
  { "ok": bool, "findings": [...], "fixes": [...] }

Findings categorized as:
  - severe: same-track collision (hyperframes will misorder)
  - warning: unintended visible overlap >0.7s without declared transition

Auto-fixes proposed (for verify.py):
  - "move_to_unique_track": rewrite track_index to deconflict
  - "tighten_overlap": shrink earlier clip's duration so overlap is ≤ 0.5s

Usage:
    python3 check_overlap.py storyboard.json [--json]
"""
import argparse
import json
import sys
from pathlib import Path

OVERLAP_TOLERANCE = 0.7  # seconds; below this we treat as deliberate cross-fade


def get_track(seg):
    """Infer track index from segment if not explicit."""
    if "track_index" in seg:
        return seg["track_index"]
    # Default routing: a-roll → 1, b-roll/title/wordmark/device/meta → 2+, audio → -1
    t = seg.get("type", "")
    if t == "a-roll":
        return 1
    return 2  # everything else lands on track 2 in the default scaffold


def overlap_amount(a, b):
    """Returns seconds of overlap between segment a and b (0 if no overlap)."""
    start = max(a["start"], b["start"])
    end = min(a["start"] + a["duration"], b["start"] + b["duration"])
    return max(0, end - start)


def check(storyboard):
    segments = storyboard["segments"]
    findings = []
    fixes = []
    pairs_checked = 0

    for i in range(len(segments)):
        for j in range(i + 1, len(segments)):
            a, b = segments[i], segments[j]
            pairs_checked += 1
            ov = overlap_amount(a, b)
            if ov <= 0:
                continue
            ta, tb = get_track(a), get_track(b)
            # Severe: same-track collision
            if ta == tb and ov > 0.05:
                findings.append(
                    {
                        "severity": "severe",
                        "code": "same_track_collision",
                        "message": (
                            f"segments {a['id']} and {b['id']} share track {ta} "
                            f"and overlap by {ov:.2f}s — hyperframes requires unique "
                            f"tracks for concurrent clips"
                        ),
                        "segments": [a["id"], b["id"]],
                    }
                )
                fixes.append(
                    {
                        "action": "move_to_unique_track",
                        "segment": b["id"],
                        "new_track": max(ta, tb) + 1,
                    }
                )
            # Warning: long unintended overlap on different tracks
            elif ov > OVERLAP_TOLERANCE:
                # Acceptable if later segment declares transition_in (means it's
                # supposed to cross-fade in over the previous one)
                later = b if b["start"] > a["start"] else a
                if not later.get("transition_in") or later["transition_in"] == "cut":
                    findings.append(
                        {
                            "severity": "warning",
                            "code": "unintended_overlap",
                            "message": (
                                f"segments {a['id']} (tk={ta}) and {b['id']} (tk={tb}) "
                                f"overlap by {ov:.2f}s but later segment has no "
                                f"transition_in declared — likely unintended visual stacking"
                            ),
                            "segments": [a["id"], b["id"]],
                        }
                    )
                    fixes.append(
                        {
                            "action": "tighten_overlap",
                            "shrink_segment": a["id"] if a["start"] < b["start"] else b["id"],
                            "new_duration": (
                                a["duration"] - (ov - 0.5)
                                if a["start"] < b["start"]
                                else b["duration"] - (ov - 0.5)
                            ),
                        }
                    )

    return {
        "ok": all(f["severity"] != "severe" for f in findings),
        "checked_pairs": pairs_checked,
        "findings": findings,
        "fixes": fixes,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    sb = json.loads(args.storyboard.read_text())
    result = check(sb)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(
            f"check_overlap: checked {result['checked_pairs']} pair(s), "
            f"{len(result['findings'])} finding(s)"
        )
        for f in result["findings"]:
            print(f"  [{f['severity']:7}] {f['code']}: {f['message']}")
    sys.exit(0 if result["ok"] else 2)


if __name__ == "__main__":
    main()
