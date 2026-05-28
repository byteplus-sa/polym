#!/usr/bin/env python3
"""
Unified verification orchestrator with auto-fix loop (Wave 5).

Runs every validator the skill ships and aggregates results into one report.
With --auto-fix, attempts mechanical repairs for the subset of issues that
have a defined fix recipe, then re-verifies. Loops up to --max-iter times
or until no severe issues remain.

What it runs:
  PRE-RENDER (when --mode pre or --mode all):
    - audit_storyboard.py    (dead air, duration, density, overflow estimate, mode)
    - check_overlap.py       (z-layer collisions, unintended visible overlap)
    - check_assets.py        (asset existence + embedded-video keyframes)
    - hyperframes lint+validate+inspect  (via `npm run check`)

  POST-RENDER (when --mode post or --mode all):
    - validate_overflow.py   (pixel-based edge bleed detection)
    - check_render_spec.py   (resolution / fps / duration vs storyboard)
    - check_audio_levels.py  (clipping + mean volume in mode-target range)

Auto-fixes implemented (--auto-fix):
  - cap camera_path scales that would overflow canvas (writes back storyboard.json)
  - re-encode embedded video with dense keyframes
  - re-mux MP4 with adjusted audio gain
  - tighten overlapping segment durations
  - move colliding segment to a unique track

Auto-fixes NOT implemented (must be surfaced to user/LLM):
  - dead air resolution (semantic — needs storyboard rewrite)
  - duration over-budget (semantic — needs content cuts)
  - missing assets (must be supplied)
  - text contrast (color space changes are risky)

Usage:
    # Pre-render verification, no auto-fix
    python3 verify.py storyboard.json --mode pre

    # Full pre+post verification with auto-fix loop (capped at 3 iterations)
    python3 verify.py storyboard.json --mode all \\
        --rendered dist/main.mp4 \\
        --project-root . \\
        --auto-fix --max-iter 3

    # JSON output for machine consumption
    python3 verify.py storyboard.json --mode pre --json
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()


def run_validator(cmd: list, label: str) -> dict:
    """Run a validator script with --json and parse its output."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return {
            "label": label,
            "ok": False,
            "findings": [
                {"severity": "severe", "code": "validator_timeout", "message": f"{label} timed out"}
            ],
            "fixes": [],
        }
    if r.returncode not in (0, 1, 2):
        return {
            "label": label,
            "ok": False,
            "findings": [
                {
                    "severity": "severe",
                    "code": "validator_crash",
                    "message": f"{label} crashed (code {r.returncode}): {r.stderr[:200]}",
                }
            ],
            "fixes": [],
        }
    try:
        result = json.loads(r.stdout)
        result["label"] = label
        return result
    except json.JSONDecodeError:
        return {
            "label": label,
            "ok": False,
            "findings": [
                {
                    "severity": "severe",
                    "code": "non_json_output",
                    "message": f"{label} did not produce JSON: {r.stdout[:200]}",
                }
            ],
            "fixes": [],
        }


def run_hyperframes_check(project_root: Path) -> dict:
    """Run the standard `npm run check` and surface lint/validate/inspect errors."""
    try:
        r = subprocess.run(
            ["npm", "run", "check"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {
            "label": "hyperframes_check",
            "ok": False,
            "findings": [
                {
                    "severity": "severe",
                    "code": "hyperframes_unavailable",
                    "message": "npm run check failed to start (Node not installed?)",
                }
            ],
            "fixes": [],
        }
    findings = []
    text = r.stdout + r.stderr
    # Crude: count error/warning summary lines
    if "error(s)" in text:
        # Extract numbers from lines like "0 error(s), 5 warning(s)"
        import re
        m = re.search(r"(\d+)\s+error\(s\),\s+(\d+)\s+warning\(s\)", text)
        if m:
            errors, warnings = int(m.group(1)), int(m.group(2))
            if errors > 0:
                findings.append(
                    {
                        "severity": "severe",
                        "code": "hyperframes_lint_errors",
                        "message": f"hyperframes check reports {errors} error(s) — run `npm run check` for details",
                    }
                )
            if warnings > 0:
                findings.append(
                    {
                        "severity": "warning",
                        "code": "hyperframes_lint_warnings",
                        "message": f"hyperframes check reports {warnings} warning(s)",
                    }
                )
    # No JSON-level auto-fix for hyperframes lint — would need finer-grained parsing
    return {
        "label": "hyperframes_check",
        "ok": all(f["severity"] != "severe" for f in findings),
        "findings": findings,
        "fixes": [],
    }


def apply_fix(fix: dict, storyboard_path: Path) -> tuple:
    """Attempt to apply one mechanical fix. Returns (success, description)."""
    action = fix.get("action")
    if action == "cap_camera_scale":
        sb = json.loads(storyboard_path.read_text())
        seg = next((s for s in sb["segments"] if s["id"] == fix["segment"]), None)
        if not seg or "camera_path" not in seg:
            return False, f"segment {fix['segment']!r} has no camera_path"
        kf = next((k for k in seg["camera_path"] if k.get("at") == fix["at"]), None)
        if not kf:
            return False, f"camera_path keyframe at {fix['at']} not found"
        kf["scale"] = fix["safe_scale"]
        storyboard_path.write_text(json.dumps(sb, indent=2))
        return True, f"capped {seg['id']} camera scale at {fix['at']}s to {fix['safe_scale']}"

    if action == "reencode_video":
        inp = fix["input"]
        out = fix["output"] + ".tmp.mp4"
        ffargs = ["ffmpeg", "-y", "-i", inp] + fix["ffmpeg_args"] + [out]
        try:
            r = subprocess.run(ffargs, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired:
            return False, f"reencode of {inp} timed out"
        if r.returncode != 0:
            return False, f"ffmpeg failed: {r.stderr[:150]}"
        Path(out).replace(fix["output"])
        return True, f"re-encoded {Path(inp).name} with dense keyframes"

    if action == "remix_volume":
        inp = fix["input"]
        gain = fix["gain_db"]
        out = inp + ".tmp.mp4"
        try:
            r = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    inp,
                    "-c:v",
                    "copy",
                    "-af",
                    f"volume={gain}dB",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    out,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return False, f"remix of {inp} timed out"
        if r.returncode != 0:
            return False, f"ffmpeg remix failed: {r.stderr[:150]}"
        Path(out).replace(inp)
        return True, f"adjusted audio gain by {gain:+.2f} dB"

    if action == "move_to_unique_track":
        sb = json.loads(storyboard_path.read_text())
        seg = next((s for s in sb["segments"] if s["id"] == fix["segment"]), None)
        if not seg:
            return False, f"segment {fix['segment']!r} not found"
        seg["track_index"] = fix["new_track"]
        storyboard_path.write_text(json.dumps(sb, indent=2))
        return True, f"moved {seg['id']} to track {fix['new_track']}"

    if action == "tighten_overlap":
        sb = json.loads(storyboard_path.read_text())
        seg = next((s for s in sb["segments"] if s["id"] == fix["shrink_segment"]), None)
        if not seg:
            return False, f"segment {fix['shrink_segment']!r} not found"
        old = seg["duration"]
        seg["duration"] = max(0.5, round(fix["new_duration"], 2))
        storyboard_path.write_text(json.dumps(sb, indent=2))
        return True, f"shrunk {seg['id']} duration {old}s → {seg['duration']}s to tighten overlap"

    return False, f"unknown fix action: {action!r}"


def overflow_fixes_from_audit(audit_result: dict, storyboard_path: Path) -> list:
    """Convert audit_storyboard.py overflow findings into cap_camera_scale fix dicts."""
    fixes = []
    sb = json.loads(storyboard_path.read_text())
    aspect = sb.get("aspect_ratio", "1:1")
    canvas_w = {"1:1": 1440, "9:16": 1080, "16:9": 1920}.get(aspect, 1440)
    # safe scale: 0.95 × canvas / (canvas × 0.86) = 0.95/0.86 ≈ 1.104
    safe_max = 0.95 / 0.86
    for f in audit_result.get("findings", []):
        # parse: "segment {id} camera_path at {at}s scale={s} likely pushes content..."
        msg = f.get("message", "")
        if "camera_path at" not in msg:
            continue
        import re
        m = re.search(r"segment (\S+) camera_path at ([\d.]+)s scale=([\d.]+)", msg)
        if not m:
            continue
        seg_id, at_s, scale_s = m.group(1), float(m.group(2)), float(m.group(3))
        if scale_s <= safe_max:
            continue
        fixes.append(
            {
                "action": "cap_camera_scale",
                "segment": seg_id,
                "at": at_s,
                "current_scale": scale_s,
                "safe_scale": round(safe_max, 3),
            }
        )
    return fixes


def run_pre_render(storyboard_path: Path, project_root: Path) -> list:
    """Run all pre-render validators. Returns list of validator-result dicts."""
    results = []
    results.append(
        run_validator(
            ["python3", str(SCRIPT_DIR / "audit_storyboard.py"), str(storyboard_path), "--json"],
            label="audit_storyboard",
        )
    )
    # Augment audit_storyboard's overflow findings with concrete cap-fix recipes
    audit = results[-1]
    if "findings" in audit:
        overflow_fixes = overflow_fixes_from_audit(audit, storyboard_path)
        audit.setdefault("fixes", []).extend(overflow_fixes)

    results.append(
        run_validator(
            ["python3", str(SCRIPT_DIR / "check_overlap.py"), str(storyboard_path), "--json"],
            label="check_overlap",
        )
    )
    # check_assets needs a project root with index.html — only run if project has been composed
    if (project_root / "index.html").exists():
        results.append(
            run_validator(
                [
                    "python3",
                    str(SCRIPT_DIR / "check_assets.py"),
                    "--project-root",
                    str(project_root),
                    "--json",
                ],
                label="check_assets",
            )
        )
        results.append(run_hyperframes_check(project_root))
    return results


def run_post_render(storyboard_path: Path, mp4_path: Path) -> list:
    results = []
    # validate_overflow.py — sample at every camera_path keyframe + a few extra
    sb = json.loads(storyboard_path.read_text())
    sample_times = set()
    for seg in sb["segments"]:
        for kf in seg.get("camera_path", []):
            sample_times.add(round(seg["start"] + kf.get("at", 0), 2))
        sample_times.add(round(seg["start"], 2))
        sample_times.add(round(seg["start"] + seg["duration"] - 0.5, 2))
    sample_times.discard(0)
    if not sample_times:
        sample_times = {2.0, 5.0, 10.0, 15.0, 20.0, 25.0}
    at_arg = ",".join(f"{t:.2f}" for t in sorted(sample_times)[:12])
    # validate_overflow.py emits text, not JSON — wrap it
    try:
        r = subprocess.run(
            ["python3", str(SCRIPT_DIR / "validate_overflow.py"), str(mp4_path), "--at", at_arg],
            capture_output=True,
            text=True,
            timeout=300,
        )
        findings = []
        for line in (r.stdout + r.stderr).splitlines():
            if "content within" in line and "edge" in line:
                findings.append(
                    {
                        "severity": "warning",
                        "code": "edge_intrusion",
                        "message": line.strip().lstrip("·· "),
                    }
                )
        results.append(
            {
                "label": "validate_overflow",
                "ok": r.returncode == 0,
                "findings": findings,
                "fixes": [],  # surface to user — overflow fix means re-render
            }
        )
    except subprocess.TimeoutExpired:
        results.append(
            {
                "label": "validate_overflow",
                "ok": False,
                "findings": [{"severity": "severe", "code": "validator_timeout", "message": "validate_overflow timed out"}],
                "fixes": [],
            }
        )
    results.append(
        run_validator(
            ["python3", str(SCRIPT_DIR / "check_render_spec.py"), str(storyboard_path), str(mp4_path), "--json"],
            label="check_render_spec",
        )
    )
    results.append(
        run_validator(
            ["python3", str(SCRIPT_DIR / "check_audio_levels.py"), str(storyboard_path), str(mp4_path), "--json"],
            label="check_audio_levels",
        )
    )
    return results


def aggregate(results: list) -> dict:
    severe = []
    warnings = []
    fixes = []
    for r in results:
        for f in r.get("findings", []):
            entry = {**f, "validator": r["label"]}
            if f.get("severity") == "severe":
                severe.append(entry)
            else:
                warnings.append(entry)
        for fix in r.get("fixes", []):
            fixes.append({**fix, "from_validator": r["label"]})
    return {
        "severe_count": len(severe),
        "warning_count": len(warnings),
        "fix_count": len(fixes),
        "severe": severe,
        "warnings": warnings,
        "fixes": fixes,
        "results": results,
    }


def auto_fix_pass(agg: dict, storyboard_path: Path) -> list:
    """Apply every fix in the aggregated list. Returns list of (success, description)."""
    outcomes = []
    for fix in agg["fixes"]:
        ok, msg = apply_fix(fix, storyboard_path)
        outcomes.append({"action": fix.get("action"), "ok": ok, "message": msg})
    return outcomes


def render_report(agg: dict, iteration: int = 0) -> str:
    lines = []
    if iteration > 0:
        lines.append(f"=== verification — iteration {iteration} ===")
    else:
        lines.append("=== verification ===")
    lines.append(
        f"severe: {agg['severe_count']}  warnings: {agg['warning_count']}  "
        f"auto-fixable: {agg['fix_count']}"
    )
    if agg["severe"]:
        lines.append("")
        lines.append("SEVERE:")
        for f in agg["severe"]:
            lines.append(f"  · [{f['validator']}] {f['code']}: {f['message']}")
    if agg["warnings"]:
        lines.append("")
        lines.append("warnings:")
        for f in agg["warnings"]:
            lines.append(f"  · [{f['validator']}] {f['code']}: {f['message']}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard", type=Path)
    ap.add_argument(
        "--mode", choices=["pre", "post", "all"], default="all", help="Which checks to run"
    )
    ap.add_argument("--rendered", type=Path, help="Path to rendered MP4 (required for post/all)")
    ap.add_argument(
        "--project-root", type=Path, default=Path("."), help="HyperFrames project root"
    )
    ap.add_argument("--auto-fix", action="store_true", help="Attempt mechanical fixes + re-verify")
    ap.add_argument("--max-iter", type=int, default=3, help="Max auto-fix iterations")
    ap.add_argument("--json", action="store_true", help="Emit JSON output")
    args = ap.parse_args()
    if not args.storyboard.exists():
        print(f"error: {args.storyboard} not found", file=sys.stderr)
        sys.exit(2)
    project_root = args.project_root.resolve()

    final_agg = None
    for iteration in range(args.max_iter if args.auto_fix else 1):
        results = []
        if args.mode in ("pre", "all"):
            results.extend(run_pre_render(args.storyboard, project_root))
        if args.mode in ("post", "all"):
            if not args.rendered:
                print("error: --rendered is required for post/all mode", file=sys.stderr)
                sys.exit(2)
            results.extend(run_post_render(args.storyboard, args.rendered))
        agg = aggregate(results)
        final_agg = agg
        if not args.auto_fix:
            break
        if agg["severe_count"] == 0:
            break
        if agg["fix_count"] == 0:
            # nothing mechanical to fix; surface remaining severe to user
            break
        print(render_report(agg, iteration + 1), file=sys.stderr)
        print(f"\nApplying {agg['fix_count']} auto-fix(es)…", file=sys.stderr)
        outcomes = auto_fix_pass(agg, args.storyboard)
        applied = sum(1 for o in outcomes if o["ok"])
        print(f"  {applied}/{len(outcomes)} fix(es) applied", file=sys.stderr)
        for o in outcomes:
            tag = "✓" if o["ok"] else "✗"
            print(f"  {tag} [{o['action']}] {o['message']}", file=sys.stderr)
        if applied == 0:
            break

    if args.json:
        print(json.dumps(final_agg, indent=2))
    else:
        print(render_report(final_agg))
    sys.exit(0 if final_agg["severe_count"] == 0 else 2)


if __name__ == "__main__":
    main()
