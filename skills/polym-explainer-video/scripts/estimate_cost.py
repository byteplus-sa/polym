#!/usr/bin/env python3
"""
Estimate the cost of executing a storyboard.

Reads storyboard.json and outputs a markdown cost table.

Cost model (see references/cost-rates.md):
  - Seedance 2.0 A-roll / cinematic B-roll → BytePlus ModelArk token spend.
    Token rates change; this script reports clip count + total seconds so the
    user can confirm against the live ModelArk console rate.
  - HyperFrames B-roll → $0 (local Chromium render).
  - Volcengine music → 1 track (1-3 generations if similarity retry triggers).
  - Seedream 4.5 portrait restyle → optional, 4 images per round.

Usage:
    python3 estimate_cost.py storyboard.json
    python3 estimate_cost.py storyboard.json --restyle-rounds 1
"""
import argparse
import json
import sys
from pathlib import Path

# Tool-name aliases — accept multiple ways of naming the same tool.
TOOL_ALIASES = {
    "seedance-2.0": "seedance",
    "seedance2.0": "seedance",
    "seedance-2": "seedance",
    "a-roll": "seedance",
    "aroll": "seedance",
    "hf": "hyperframes",
}


def normalize_tool(name):
    n = (name or "").lower().strip()
    return TOOL_ALIASES.get(n, n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard", help="Path to storyboard.json")
    ap.add_argument("--restyle-rounds", type=int, default=0,
                    help="Number of Seedream 4.5 portrait-restyle rounds (4 images each)")
    ap.add_argument("--music-tracks", type=int, default=1,
                    help="Number of Volcengine music generations (1-3 with retries)")
    ap.add_argument("--out", default="cost-estimate.md", help="Output markdown file")
    args = ap.parse_args()

    sb = json.loads(Path(args.storyboard).read_text())
    segments = sb.get("segments", [])

    seedance_clips = 0
    seedance_seconds = 0.0
    hyperframes_segs = 0
    rows = []

    for seg in segments:
        sid = seg.get("id", "?")
        seg_type = seg.get("type", "")
        tool = normalize_tool(seg.get("tool", ""))
        duration = float(seg.get("duration", 0))

        if tool == "seedance" or seg_type == "a-roll":
            seedance_clips += 1
            seedance_seconds += duration
            cost_str = "Seedance tokens"
        elif tool == "hyperframes":
            hyperframes_segs += 1
            cost_str = "$0"
        else:
            cost_str = "varies"

        rows.append({
            "id": sid, "type": seg_type, "tool": tool or "—",
            "duration": duration, "cost": cost_str,
        })

    lines = [
        "# Cost estimate",
        "",
        f"**Storyboard:** `{args.storyboard}`",
        "",
        "## Per-segment breakdown",
        "",
        "| # | Type | Tool | Duration | Cost |",
        "|---|------|------|----------|------|",
    ]
    for r in rows:
        lines.append(
            f"| {r['id']} | {r['type']} | {r['tool']} | {r['duration']:g}s | {r['cost']} |"
        )

    lines.extend([
        "",
        "## Totals",
        "",
        f"- **Seedance 2.0**: {seedance_clips} clip(s), {seedance_seconds:g}s total "
        f"— BytePlus ModelArk token spend (confirm rate in the ModelArk console)",
        f"- **HyperFrames B-roll**: {hyperframes_segs} segment(s) — $0 (local render)",
        f"- **Volcengine music**: {args.music_tracks} generation(s) — small per-track fee",
    ])
    if args.restyle_rounds:
        lines.append(
            f"- **Seedream 4.5 restyle**: {args.restyle_rounds} round(s) × 4 images "
            f"= {args.restyle_rounds * 4} image generation(s)"
        )
    lines.extend([
        "- **Lark upload**: $0",
        "",
        "> Seedance is token-priced and rates change — a ~90s explainer with 2 short "
        "A-roll clips is typically a single-digit USD-equivalent spend. Always confirm "
        "against the live ModelArk rate before approving the storyboard.",
    ])

    md = "\n".join(lines)
    Path(args.out).write_text(md)

    print(md)
    print(f"\n[Cost estimate saved to {args.out}]", file=sys.stderr)


if __name__ == "__main__":
    main()
