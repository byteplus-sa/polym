#!/usr/bin/env python3
"""
Orchestrator for Phase 4 — production execution.

This is mostly a guide / scaffold. The Seedance 2.0 API calls happen through Claude
Code following SKILL.md Phase 4 instructions, not from this script.

What this script DOES do:
  - Validates that all assets/*.mp4 files exist
  - Generates a HyperFrames composition (index.html) from storyboard.json
  - Runs npm run check + npm run render
  - Produces dist/main.mp4

The Seedance A-roll generation (and any cinematic Seedance B-roll) is handled by
Claude Code per SKILL.md § A-roll generation, NOT this script.

Usage:
    # After all Seedance-generated A-roll MP4s are in place:
    python3 compose_and_render.py storyboard.json
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


def resolve_dimensions(storyboard):
    """Pull aspect_ratio + width/height from storyboard (PR #1 + #12)."""
    aspect = storyboard.get("aspect_ratio", "9:16")
    w = storyboard.get("width")
    h = storyboard.get("height")
    if not w or not h:
        w, h = DEFAULT_DIMS.get(aspect, (1080, 1920))
    return w, h, aspect


def load_style_preset(storyboard, skill_root):
    """Load the design.md for the chosen style preset (PR #12).

    Returns a dict of brand tokens (palette, fonts, etc.). For now we only
    pull bg_primary and the display font family — enough for the template
    substitution. Future iterations can pass the full design.md through to
    composition authoring.
    """
    preset = storyboard.get("style_preset", "openai-clean")
    if preset == "custom":
        # User supplied their own design.md in project root
        return {
            "bg_color": "#FAFAF9",
            "font_family": '"Inter", -apple-system, "Helvetica Neue", system-ui, sans-serif',
        }
    preset_path = skill_root / "assets" / "style-presets" / preset / "design.md"
    if not preset_path.exists():
        print(f"WARN: style preset {preset!r} not found, falling back to openai-clean")
        preset = "openai-clean"
        preset_path = skill_root / "assets" / "style-presets" / preset / "design.md"
    # Crude parse — extract bg_primary + display fields from the YAML-ish blocks
    text = preset_path.read_text()
    bg = _extract_yaml_field(text, "bg_primary", default='"#FAFAF9"').strip('"')
    display = _extract_yaml_field(
        text, "display", default='"Inter"'
    ).strip('"')
    display_fb = _extract_yaml_field(
        text, "display_fallback", default='"-apple-system, system-ui, sans-serif"'
    ).strip('"')
    overrides = storyboard.get("style_overrides", {})
    bg = overrides.get("bg_primary", bg)
    return {
        "bg_color": bg,
        "font_family": f'"{display}", {display_fb}',
        "preset": preset,
    }


def _extract_yaml_field(text, key, default=""):
    """Crude single-line YAML extractor — handles `key: "value"` patterns."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(f"{key}:"):
            return stripped[len(key) + 1 :].strip()
    return default


def validate_assets(storyboard, project_root):
    """Check all required MP4 files exist and are non-empty."""
    missing = []
    empty = []
    assets_dir = project_root / "assets"

    for seg in storyboard["segments"]:
        if seg.get("tool") in ("hyperframes",):
            continue  # programmatic, no MP4 needed
        sid = seg["id"]
        mp4 = assets_dir / f"{sid}.mp4"
        if not mp4.exists():
            missing.append(str(mp4))
        elif mp4.stat().st_size < 1024:
            empty.append(str(mp4))

    return missing, empty


def install_registry_blocks(storyboard, project_root):
    """Install any registry blocks declared in the storyboard (PR #4)."""
    blocks = []
    for seg in storyboard["segments"]:
        b = seg.get("block")
        if b and b not in blocks:
            blocks.append(b)
    if not blocks:
        return True
    print(f"Installing {len(blocks)} registry block(s): {', '.join(blocks)}")
    for b in blocks:
        r = subprocess.run(
            ["npx", "--yes", "hyperframes@0.4.43", "add", b, "--no-clipboard"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            print(f"  WARN: hyperframes add {b} failed:\n{r.stderr}", file=sys.stderr)
            return False
        print(f"  ✓ {b}")
    return True


def generate_composition(storyboard, project_root, template_path, skill_root=None):
    """
    Generate index.html from storyboard.json + template.

    The template has placeholder markers we replace with real segments.
    For complex animations the user / Claude Code may need to hand-edit afterwards.
    """
    template = template_path.read_text()
    total_duration = storyboard.get("total_duration", 15.0)
    width, height, _ = resolve_dimensions(storyboard)
    style = load_style_preset(storyboard, skill_root) if skill_root else {
        "bg_color": "#FAFAF9",
        "font_family": '"Inter", -apple-system, system-ui, sans-serif',
    }

    elements = []
    timeline = []

    for seg in storyboard["segments"]:
        sid = seg["id"]
        start = seg["start"]
        duration = seg["duration"]
        tool = seg.get("tool", "")
        seg_type = seg.get("type", "")

        if seg_type == "a-roll":
            # Insert <video> + <audio> for a Seedance A-roll segment
            # (Seedance A-roll carries its own native audio)
            mp4 = f"assets/{sid}.mp4"
            elements.append(f"""
      <video id="{sid}" class="clip" data-start="{start}" data-duration="{duration}"
             data-track-index="1" src="{mp4}" muted></video>
      <audio id="{sid}-audio" class="clip" data-start="{start}" data-duration="{duration}"
             data-track-index="3" src="{mp4}"></audio>""")
            cap = seg.get("caption")
            if cap:
                cap_start = seg.get("caption_start", start + 0.3)
                cap_dur = seg.get("caption_duration", duration - 0.5)
                elements.append(f"""
      <div id="{sid}-caption" class="clip caption" data-start="{cap_start}"
           data-duration="{cap_dur}" data-track-index="2">
        <span class="caption-bg">{cap}</span>
      </div>""")
                timeline.append(
                    f'      tl.from("#{sid}-caption", {{opacity: 0, y: 30, duration: 0.4}}, {cap_start});\n'
                    f'      tl.to("#{sid}-caption", {{opacity: 0, duration: 0.2}}, {cap_start + cap_dur - 0.2});\n'
                    f'      tl.set("#{sid}-caption", {{opacity: 0}}, {cap_start + cap_dur});'
                )

        elif tool == "seedance" or seg_type == "b-roll-video":
            # Cinematic Seedance B-roll — video only, no caption-track audio
            mp4 = f"assets/{sid}.mp4"
            elements.append(f"""
      <video id="{sid}" class="clip" data-start="{start}" data-duration="{duration}"
             data-track-index="1" src="{mp4}" muted></video>""")
            cap = seg.get("caption")
            if cap:
                cap_start = seg.get("caption_start", start + 0.3)
                cap_dur = seg.get("caption_duration", duration - 0.5)
                elements.append(f"""
      <div id="{sid}-caption" class="clip caption" data-start="{cap_start}"
           data-duration="{cap_dur}" data-track-index="2">
        <span class="caption-bg">{cap}</span>
      </div>""")
                timeline.append(
                    f'      tl.from("#{sid}-caption", {{opacity: 0, y: 30, duration: 0.4}}, {cap_start});\n'
                    f'      tl.to("#{sid}-caption", {{opacity: 0, duration: 0.2}}, {cap_start + cap_dur - 0.2});\n'
                    f'      tl.set("#{sid}-caption", {{opacity: 0}}, {cap_start + cap_dur});'
                )

        elif tool == "hyperframes":
            # This is where we'd render programmatic scene from spec.
            # For complex specs, leave a stub the user/Claude Code edits manually.
            elements.append(f"""
      <!-- HYPERFRAMES_SCENE id={sid} duration={duration} -->
      <div id="{sid}" class="clip hyperframes-scene"
           data-start="{start}" data-duration="{duration}" data-track-index="1"
           style="background:#0a0a0a;color:#fff;display:flex;align-items:center;justify-content:center;font-size:32px;">
        <!-- TODO: implement scene per storyboard spec -->
        Scene {sid}: {seg.get('intent', '')[:50]}
      </div>""")

    # Inject into template — fill all placeholders (PR #1 + #12 — templated dims + style)
    template = template.replace("<!-- ELEMENTS_PLACEHOLDER -->", "\n".join(elements))
    template = template.replace("// TIMELINE_PLACEHOLDER", "\n".join(timeline))
    template = template.replace("DURATION_PLACEHOLDER", str(total_duration))
    template = template.replace("WIDTH_PLACEHOLDER", str(width))
    template = template.replace("HEIGHT_PLACEHOLDER", str(height))
    template = template.replace("BG_COLOR_PLACEHOLDER", style["bg_color"])
    template = template.replace("FONT_FAMILY_PLACEHOLDER", style["font_family"])

    out_path = project_root / "index.html"
    out_path.write_text(template)
    print(f"✓ Generated {out_path}")


def run_lint(project_root):
    print("Running lint...")
    r = subprocess.run(["npm", "run", "check"], cwd=project_root,
                       capture_output=True, text=True)
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        return False
    return True


def run_verify(storyboard_path, project_root, rendered=None, mode="pre", auto_fix=True, max_iter=3):
    """Invoke verify.py (Wave 5). Returns True if no severe issues remain."""
    cmd = [
        "python3",
        str(Path(__file__).parent / "verify.py"),
        str(storyboard_path),
        "--mode",
        mode,
        "--project-root",
        str(project_root),
        "--max-iter",
        str(max_iter),
    ]
    if auto_fix:
        cmd.append("--auto-fix")
    if rendered:
        cmd.extend(["--rendered", str(rendered)])
    print(f"--- verify ({mode}{' +auto-fix' if auto_fix else ''}) ---")
    r = subprocess.run(cmd)
    return r.returncode == 0


def run_render(project_root, fps=60, quality="high"):
    """Render at 60fps high quality by default (PR #2).

    Bypasses `npm run render` (which uses the package.json default 30fps) and calls
    hyperframes directly so we control the flags. See references/motion-house-style.md §1.
    """
    print(f"Running render at {fps}fps quality={quality} (this may take 3-6 min)...")
    r = subprocess.run(
        [
            "npx",
            "--yes",
            "hyperframes@0.4.43",
            "render",
            ".",
            "--fps",
            str(fps),
            "--quality",
            quality,
            "--workers",
            "4",
        ],
        cwd=project_root,
    )
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard", help="Path to storyboard.json")
    ap.add_argument("--project-root", default=".", help="HyperFrames project root")
    ap.add_argument("--template",
                    help="Path to hyperframes-template.html (defaults to ./assets/hyperframes-template.html)")
    ap.add_argument("--skip-validate", action="store_true",
                    help="Skip MP4 file existence check")
    ap.add_argument("--skip-render", action="store_true",
                    help="Generate composition only, don't render")
    ap.add_argument("--fps", type=int, default=60,
                    help="Render frame rate (default 60 — see motion-house-style.md §1)")
    ap.add_argument("--quality", default="high", choices=["draft", "standard", "high"],
                    help="Render quality (default high)")
    ap.add_argument("--no-auto-fix", action="store_true",
                    help="(Wave 5) Skip the auto-fix loop in verify.py; report issues only")
    ap.add_argument("--verify-max-iter", type=int, default=3,
                    help="(Wave 5) Max auto-fix iterations per verify pass (default 3)")
    ap.add_argument("--force", action="store_true",
                    help="Render even if pre-render verification has severe issues")
    args = ap.parse_args()

    storyboard = json.loads(Path(args.storyboard).read_text())
    project_root = Path(args.project_root).resolve()
    skill_root = Path(__file__).parent.parent.resolve()  # ~/.claude/skills/explainer-video

    template_path = (Path(args.template) if args.template
                     else project_root / "assets" / "hyperframes-template.html")
    if not template_path.exists():
        # try repo path as fallback
        template_path = Path(__file__).parent.parent / "assets" / "hyperframes-template.html"
    if not template_path.exists():
        print(f"ERROR: template not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    if not args.skip_validate:
        missing, empty = validate_assets(storyboard, project_root)
        if missing:
            print(f"ERROR: missing MP4 files (Phase 4 step 3-4 incomplete):", file=sys.stderr)
            for m in missing:
                print(f"  - {m}", file=sys.stderr)
            sys.exit(1)
        if empty:
            print(f"ERROR: empty MP4 files:", file=sys.stderr)
            for m in empty:
                print(f"  - {m}", file=sys.stderr)
            sys.exit(1)

    # Install any registry blocks the storyboard references (PR #4)
    if not install_registry_blocks(storyboard, project_root):
        print("Registry block install failed.", file=sys.stderr)
        sys.exit(1)

    generate_composition(storyboard, project_root, template_path, skill_root)

    if args.skip_render:
        print("Composition generated. Run `npm run check && npm run render` manually.")
        return

    # === Pre-render verify with auto-fix (Wave 5) ===
    # Catches storyboard issues + asset issues + lint errors BEFORE wasting render time
    pre_ok = run_verify(
        Path(args.storyboard).resolve(),
        project_root,
        mode="pre",
        auto_fix=not args.no_auto_fix,
        max_iter=args.verify_max_iter,
    )
    if not pre_ok and not args.force:
        print(
            "Pre-render verification has severe issues. Use --force to render anyway, "
            "or fix the issues and re-run.",
            file=sys.stderr,
        )
        sys.exit(1)
    # If auto-fix modified the storyboard, regenerate composition before render
    new_sb = json.loads(Path(args.storyboard).read_text())
    if new_sb != storyboard:
        print("Storyboard was auto-fixed; regenerating composition…")
        generate_composition(new_sb, project_root, template_path, skill_root)
        storyboard = new_sb

    if not run_render(project_root, fps=args.fps, quality=args.quality):
        print("Render failed.", file=sys.stderr)
        sys.exit(1)

    # === Post-render verify (Wave 5) ===
    rendered_mp4 = project_root / "dist" / "main.mp4"
    if rendered_mp4.exists():
        post_ok = run_verify(
            Path(args.storyboard).resolve(),
            project_root,
            rendered=rendered_mp4,
            mode="post",
            auto_fix=not args.no_auto_fix,
            max_iter=args.verify_max_iter,
        )
        if not post_ok:
            print(
                "Post-render verification has severe issues. The MP4 was produced but "
                "may have quality problems — review the report above.",
                file=sys.stderr,
            )

    print("\n✓ Production complete. Output: dist/main.mp4")


if __name__ == "__main__":
    main()
