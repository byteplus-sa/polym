#!/usr/bin/env python3
"""
Storyboard auditor — PR #7 (dead-air detector) + PR #11 (duration target & pacing).

Runs in Phase 3 BEFORE the approval gate. Flags structural issues that
would otherwise be discovered only after rendering:

  - dead-air: any window ≥ 3s in a segment with no visual events
  - over-budget: total duration > 130% of profile target
  - segment-too-long: any single segment > 8s without internal beat changes
  - duplicate-adjacent: two adjacent segments with near-identical content
  - missing-beats: device-mockup / long B-roll segments without beats[]
  - tool-mismatch: A-roll specified but mode != aroll-broll-hybrid

Outputs human-readable warnings + a machine JSON dump so Phase 3 can
auto-suggest fixes.

Usage:
    python3 audit_storyboard.py storyboard.json
    python3 audit_storyboard.py storyboard.json --json
    python3 audit_storyboard.py storyboard.json --profile single-message
"""
import argparse
import json
import sys
from pathlib import Path

# Profile-based duration recommendations (PR #11 — revised from the v0 SKILL.md table)
PROFILE_TARGETS = {
    "single-message": (25, 35),
    "few-features": (40, 55),
    "many-features": (65, 90),
}

# Default beats per segment type — if a segment of this type has < this many
# `beats[]` entries, it's likely going to feel static.
MIN_BEATS_BY_TYPE = {
    "device-mockup": 4,
    "data-viz": 2,
    "title-card": 1,
    "wordmark": 1,
    "meta-output": 2,  # multi-shot preview from PR #8
    "breather": 1,     # intentional minimal beats — see narrative-arc.md Pattern 6
}


def _seg_events(seg):
    """Count distinct visual events in a segment.

    Events that count:
      - Each entry in `beats[]` (if present)
      - Each `shots[]` entry for `meta-output` segments (PR #8 multi-shot beat)
      - Each `camera_path[]` keyframe past the first (from PR #6)
      - `transition_in` (counts as 1 event at segment start)
      - A `script` (A-roll spoken line — counts as continuous event)
    """
    events = []
    if seg.get("transition_in") and seg.get("transition_in") != "cut":
        events.append((seg["start"], "transition_in"))
    # Beats — `at` is RELATIVE to segment start (canonical format per storyboard-format.md)
    for b in seg.get("beats", []):
        at_rel = b.get("at", 0.0)
        events.append((seg["start"] + at_rel, f"beat:{b.get('name', '?')}"))
    # PR #8 — meta-output segments use shots[] instead of beats[]
    if seg.get("type") == "meta-output":
        for s in seg.get("shots", []):
            at = seg["start"] + s.get("start_offset", 0.0)
            events.append((at, f"shot:{s.get('id', '?')}"))
    cam = seg.get("camera_path", [])
    for i, kf in enumerate(cam):
        if i == 0:
            continue  # initial keyframe isn't an "event"
        events.append((seg["start"] + kf.get("at", 0.0), f"camera:{kf.get('scale', '?')}"))
    if seg.get("script"):
        # A-roll script "covers" the whole segment with continuous event-ness
        events.append((seg["start"] + 0.5, "script:speaking"))
        events.append((seg["start"] + seg["duration"] - 0.5, "script:end"))
    return sorted(events)


def check_dead_air(seg, max_gap=3.0):
    """Find windows within a segment that have no events for > max_gap seconds."""
    events = _seg_events(seg)
    seg_start = seg["start"]
    seg_end = seg_start + seg["duration"]
    findings = []

    if not events:
        if seg["duration"] >= max_gap:
            findings.append(
                f"segment {seg['id']} ({seg_start:.1f}-{seg_end:.1f}s, "
                f"{seg['duration']:.1f}s) has zero declared visual events"
            )
        return findings

    # gap before first event
    if events[0][0] - seg_start > max_gap:
        findings.append(
            f"segment {seg['id']}: {seg_start:.1f}-{events[0][0]:.1f}s "
            f"({events[0][0] - seg_start:.1f}s gap before first event)"
        )
    # gaps between consecutive events
    for i in range(len(events) - 1):
        gap = events[i + 1][0] - events[i][0]
        if gap > max_gap:
            findings.append(
                f"segment {seg['id']}: {events[i][0]:.1f}-{events[i + 1][0]:.1f}s "
                f"({gap:.1f}s gap between events)"
            )
    # gap after last event
    if seg_end - events[-1][0] > max_gap:
        findings.append(
            f"segment {seg['id']}: {events[-1][0]:.1f}-{seg_end:.1f}s "
            f"({seg_end - events[-1][0]:.1f}s gap after last event)"
        )
    return findings


def check_segment_density(seg):
    """Flag segments long enough that they need internal beats."""
    findings = []
    seg_type = seg.get("type", "")
    min_beats = MIN_BEATS_BY_TYPE.get(seg_type)
    if not min_beats:
        return findings
    declared_beats = len(seg.get("beats", []))
    if seg["duration"] >= 8 and declared_beats < min_beats:
        findings.append(
            f"segment {seg['id']} (type={seg_type}, {seg['duration']:.1f}s) declares "
            f"{declared_beats} beat(s); type recommends ≥ {min_beats}. "
            f"Add beats[] entries or compress duration."
        )
    return findings


def check_duration_target(storyboard, profile):
    findings = []
    total = storyboard.get("total_duration") or sum(
        s["duration"] for s in storyboard["segments"]
    )
    if profile not in PROFILE_TARGETS:
        findings.append(
            f"unknown content_profile {profile!r} — expected one of "
            f"{list(PROFILE_TARGETS.keys())}"
        )
        return findings, total
    lo, hi = PROFILE_TARGETS[profile]
    over_threshold = hi * 1.30
    if total > over_threshold:
        findings.append(
            f"total duration {total:.1f}s exceeds {profile} target ({lo}-{hi}s) "
            f"by >30% — compress or split content"
        )
    elif total < lo * 0.7:
        findings.append(
            f"total duration {total:.1f}s is shorter than {profile} target "
            f"({lo}-{hi}s) — consider adding a beat or extending"
        )
    return findings, total


def check_adjacent_duplicates(segments):
    """Flag adjacent segments with near-identical intent/title."""
    findings = []
    for i in range(len(segments) - 1):
        a, b = segments[i], segments[i + 1]
        a_text = (a.get("intent") or a.get("title") or "").strip().lower()
        b_text = (b.get("intent") or b.get("title") or "").strip().lower()
        if a_text and a_text == b_text:
            findings.append(
                f"segments {a['id']} and {b['id']} have identical content "
                f"({a_text!r}) — merge or differentiate"
            )
    return findings


def check_mode_consistency(storyboard):
    """Flag A-roll segments when mode is pure-broll."""
    findings = []
    mode = storyboard.get("mode", "aroll-broll-hybrid")
    if mode == "pure-broll-product-demo":
        for seg in storyboard["segments"]:
            if seg.get("type") == "a-roll" or seg.get("tool") == "seedance":
                findings.append(
                    f"segment {seg['id']} uses A-roll/Seedance but mode is "
                    f"{mode!r} — remove the segment or change mode"
                )
    return findings


def check_overflow_camera(storyboard):
    """Flag camera_path with scale that mathematically pushes content off canvas.

    Rough rule: at any scale s, with default macbook width 1240px in a 1440px
    canvas, max safe scale is ~1.15 (1240 × 1.15 = 1426 px, fits with 7px margin).
    """
    findings = []
    aspect = storyboard.get("aspect_ratio", "1:1")
    canvas_w = {"1:1": 1440, "9:16": 1080, "16:9": 1920}.get(aspect, 1440)
    for seg in storyboard["segments"]:
        for kf in seg.get("camera_path", []):
            s = kf.get("scale", 1.0)
            # Assume a primary content element ~ 86% of canvas width at scale 1.
            content_at_scale = canvas_w * 0.86 * s
            if content_at_scale > canvas_w * 0.98:
                findings.append(
                    f"segment {seg['id']} camera_path at {kf.get('at', '?')}s "
                    f"scale={s} likely pushes content off canvas (estimated "
                    f"{int(content_at_scale)}px in {canvas_w}px-wide frame). "
                    f"Reduce max scale to ~1.15 or shift transform-origin."
                )
    return findings


ABSTRACT_PROTAGONIST_TOKENS = ("user", "viewer", "developer", "founder", "person", "people", "anyone")


def check_narrative_arc(storyboard):
    """Verify the storyboard has a narrative arc (see references/narrative-arc.md)."""
    findings = []
    narrative = storyboard.get("narrative", {})
    arc_map = storyboard.get("arc_map", {})

    required_narrative = ["protagonist", "problem", "moment_of_magic", "memorable_line"]
    missing = [k for k in required_narrative if not narrative.get(k)]
    if missing:
        findings.append(
            f"missing narrative field(s): {', '.join(missing)} — read "
            f"references/narrative-arc.md and fill these in BEFORE drafting segments"
        )

    # Detect REPLACE: placeholders left over from the recipe template
    placeholders = [
        k for k, v in narrative.items()
        if isinstance(v, str) and "REPLACE" in v
    ]
    if placeholders:
        findings.append(
            f"narrative field(s) still contain 'REPLACE:' placeholders: "
            f"{', '.join(placeholders)} — fill them with real values"
        )

    expected_beats = ["hook", "tension", "reveal", "magic", "promise"]
    if not arc_map:
        findings.append(
            "missing arc_map — map each segment to one of: hook / tension / reveal "
            "/ magic / promise. See references/narrative-arc.md"
        )
    else:
        for beat in expected_beats:
            if beat not in arc_map or not arc_map[beat]:
                findings.append(
                    f"arc_map missing beat {beat!r} — every video needs all 5 beats; "
                    f"if you genuinely don't have content for this beat, the storyboard "
                    f"is incomplete (don't render a story without resolution)"
                )

        # Magic beat should be the largest by combined duration
        beat_durations = {}
        segs_by_id = {s["id"]: s for s in storyboard["segments"]}
        for beat, seg_ids in arc_map.items():
            total = sum(segs_by_id.get(sid, {}).get("duration", 0) for sid in seg_ids)
            beat_durations[beat] = total
        if beat_durations.get("magic", 0) > 0:
            longest_beat = max(beat_durations, key=beat_durations.get)
            if longest_beat != "magic" and beat_durations["magic"] < beat_durations[longest_beat] * 0.7:
                findings.append(
                    f"the 'magic' beat is only {beat_durations['magic']:.1f}s but "
                    f"'{longest_beat}' is {beat_durations[longest_beat]:.1f}s — the "
                    f"magic moment should be the longest combined beat (it's the "
                    f"reason the video exists). Re-balance segment durations."
                )

    # Anti-pattern: 3+ device-mockup segments with no narrative arc — screen catalogue
    device_segs = [s for s in storyboard["segments"] if s.get("type") == "device-mockup"]
    if len(device_segs) >= 3 and not arc_map:
        findings.append(
            "3+ device-mockup segments without arc_map — likely a 'screen catalogue' "
            "(sequence of UI views with no story). Read references/narrative-arc.md."
        )
    return findings


def check_canon(storyboard):
    """Pattern 1 — verify canon has 3+ specific entities."""
    findings = []
    canon = storyboard.get("canon", {})
    if not canon:
        findings.append(
            "missing 'canon' field — list 3-5 specific entities (named meeting / person / "
            "quote / doc) preserved across every frame. See narrative-arc.md Pattern 1."
        )
        return findings
    real_entries = [v for v in canon.values() if v and (not isinstance(v, str) or "REPLACE" not in v)]
    if len(real_entries) < 3:
        findings.append(
            f"canon only has {len(real_entries)} entries — need at least 3 specific entities "
            f"(names, exact quotes, exact docs) to anchor the story"
        )
    return findings


def check_cast(storyboard):
    """Pattern 3 — verify cast has a named protagonist (not abstract)."""
    findings = []
    cast = storyboard.get("cast", {})
    if not cast:
        findings.append(
            "missing 'cast' field — declare a named protagonist + supporting cast. "
            "See narrative-arc.md Pattern 3."
        )
        return findings
    protagonist = cast.get("protagonist", {})
    name = (protagonist.get("name") or "").strip().lower()
    if not name:
        findings.append("cast.protagonist.name is empty — give them a real name")
    elif name in ABSTRACT_PROTAGONIST_TOKENS or "REPLACE" in name:
        findings.append(
            f"cast.protagonist.name {name!r} is too abstract — use a specific name "
            f"(e.g., 'Erica', not 'the user')"
        )
    return findings


def check_echo(storyboard):
    """Pattern 2 — verify at least one echo spans 2+ frames."""
    findings = []
    echoes = storyboard.get("echo", [])
    if not echoes:
        findings.append(
            "missing 'echo' field — pick one canon entity that recurs across 2+ frames "
            "as a visual rhyme. The central beat of the story. See narrative-arc.md Pattern 2."
        )
        return findings
    seg_ids = {s["id"] for s in storyboard["segments"]}
    for e in echoes:
        appears = e.get("appears_in", [])
        if len(appears) < 2:
            findings.append(
                f"echo {e.get('artifact', '?')!r} appears in only {len(appears)} frame(s) — "
                f"an echo needs 2+ recurrences to be a rhyme"
            )
        missing = [f for f in appears if f not in seg_ids]
        if missing:
            findings.append(
                f"echo {e.get('artifact', '?')!r} references frames not in storyboard: {missing}"
            )
    return findings


def check_narration_coverage(storyboard):
    """Pattern 5 — every segment must declare narration OR explicit silent."""
    findings = []
    for seg in storyboard["segments"]:
        narration = seg.get("narration")
        if not narration:
            findings.append(
                f"segment {seg['id']!r} has no 'narration' field — declare either a "
                f"narration cue OR explicit {{silent: true}}. No frame is allowed without one."
            )
            continue
        if narration.get("silent"):
            if not narration.get("reason"):
                findings.append(
                    f"segment {seg['id']!r} narration.silent=true but no 'reason' given"
                )
        else:
            if not narration.get("line"):
                findings.append(
                    f"segment {seg['id']!r} narration not silent but 'line' is empty"
                )
            if not narration.get("cue_id"):
                findings.append(
                    f"segment {seg['id']!r} narration missing 'cue_id' (e.g., '03 · DETECT')"
                )
    return findings


def check_frame_names(storyboard):
    """Pattern 4 — every segment should have a short UPPERCASE frame_name."""
    findings = []
    for seg in storyboard["segments"]:
        fn = seg.get("frame_name")
        if not fn:
            findings.append(
                f"segment {seg['id']!r} missing 'frame_name' — give it a short UPPERCASE "
                f"keyword (e.g., 'SUMMON', 'DETECT', 'KEPT')"
            )
        elif fn != fn.upper() or len(fn) > 24:
            findings.append(
                f"segment {seg['id']!r} frame_name {fn!r} should be UPPERCASE and ≤ 24 chars"
            )
    return findings


def check_click_chain(storyboard):
    """Pattern 7 — verify click_chain timestamps align with next frame's start (±0.2s)."""
    findings = []
    chain = storyboard.get("click_chain", [])
    if not chain:
        return findings  # optional pattern
    segs_by_id = {s["id"]: s for s in storyboard["segments"]}
    for click in chain:
        trig_id = click.get("triggers")
        click_at = click.get("at")
        if not trig_id or click_at is None:
            findings.append(f"click_chain entry malformed: {click}")
            continue
        next_seg = segs_by_id.get(trig_id)
        if not next_seg:
            findings.append(f"click_chain triggers unknown segment {trig_id!r}")
            continue
        gap = abs(next_seg["start"] - click_at)
        # Production storylines have click → feedback animation → next scene, so
        # 1-2s gap is normal. Flag only if implausibly large (>3s) — likely a misdeclaration.
        if gap > 3.0:
            findings.append(
                f"click_chain at {click_at}s claims to trigger {trig_id!r} but that segment "
                f"starts at {next_seg['start']}s (gap {gap:.2f}s > 3.0s — likely misdeclared)"
            )
    return findings


def audit(storyboard, profile_override=None):
    """Run all checks. Returns (findings_list, summary_dict)."""
    profile = profile_override or storyboard.get("content_profile", "few-features")
    findings = {
        "dead_air": [],
        "density": [],
        "duration": [],
        "duplicates": [],
        "mode": [],
        "overflow": [],
        "narrative": [],
        "canon": [],
        "cast": [],
        "echo": [],
        "narration": [],
        "frame_names": [],
        "click_chain": [],
    }

    for seg in storyboard["segments"]:
        findings["dead_air"].extend(check_dead_air(seg))
        findings["density"].extend(check_segment_density(seg))

    dur_findings, total = check_duration_target(storyboard, profile)
    findings["duration"].extend(dur_findings)
    findings["duplicates"].extend(check_adjacent_duplicates(storyboard["segments"]))
    findings["mode"].extend(check_mode_consistency(storyboard))
    findings["overflow"].extend(check_overflow_camera(storyboard))
    findings["narrative"].extend(check_narrative_arc(storyboard))
    findings["canon"].extend(check_canon(storyboard))
    findings["cast"].extend(check_cast(storyboard))
    findings["echo"].extend(check_echo(storyboard))
    findings["narration"].extend(check_narration_coverage(storyboard))
    findings["frame_names"].extend(check_frame_names(storyboard))
    findings["click_chain"].extend(check_click_chain(storyboard))

    summary = {
        "profile": profile,
        "total_duration": total,
        "target_range": PROFILE_TARGETS.get(profile),
        "segment_count": len(storyboard["segments"]),
        "warning_count": sum(len(v) for v in findings.values()),
    }
    return findings, summary


SEVERITY_BY_CATEGORY = {
    "dead_air": "warning",
    "density": "warning",
    "duration": "warning",
    "duplicates": "warning",
    "mode": "severe",         # mode mismatches break the render pipeline
    "overflow": "warning",    # camera overflow is estimable, post-render validator confirms
    "narrative": "severe",    # storyboard without a story is a render-the-wrong-thing risk
    "canon": "severe",        # canon < 3 entities = story too abstract to land
    "cast": "warning",        # abstract protagonist is bad craft but not always a blocker
    "echo": "warning",        # missing echo = less polished but renderable
    "narration": "warning",   # missing narration on a segment is a craft issue
    "frame_names": "warning",
    "click_chain": "warning",
}


def _flatten_for_verify(findings_by_cat, summary):
    """Convert grouped findings into the flat schema verify.py expects."""
    flat = []
    for cat, items in findings_by_cat.items():
        sev = SEVERITY_BY_CATEGORY.get(cat, "warning")
        for msg in items:
            flat.append({"severity": sev, "code": cat, "message": msg})
    return {
        "ok": not any(f["severity"] == "severe" for f in flat),
        "summary": summary,
        "findings": flat,
        "fixes": [],  # auto-fix recipes are derived by verify.py for overflow only
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard", type=Path)
    ap.add_argument("--profile", help="Override content_profile")
    ap.add_argument("--json", action="store_true", help="Emit JSON output")
    args = ap.parse_args()
    if not args.storyboard.exists():
        print(f"error: {args.storyboard} not found", file=sys.stderr)
        sys.exit(2)
    sb = json.loads(args.storyboard.read_text())
    findings, summary = audit(sb, args.profile)

    if args.json:
        print(json.dumps(_flatten_for_verify(findings, summary), indent=2))
        sys.exit(1 if summary["warning_count"] else 0)

    print(f"=== storyboard audit — {args.storyboard.name} ===")
    print(
        f"profile={summary['profile']}  duration={summary['total_duration']:.1f}s  "
        f"target={summary['target_range']}  segments={summary['segment_count']}"
    )
    print()
    if summary["warning_count"] == 0:
        print("OK · no warnings.")
        return 0
    for category, items in findings.items():
        if not items:
            continue
        print(f"⚠ {category} ({len(items)}):")
        for line in items:
            print(f"  · {line}")
        print()
    print(
        f"{summary['warning_count']} warning(s) total. "
        f"Fix or justify each before approval gate."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
