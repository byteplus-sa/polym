#!/usr/bin/env python3
"""
Synthesize an in-device screen HTML+CSS from product context — PR #5.

Given a product brief + a few reference screenshots, asks Claude to
generate semantically faithful HTML+CSS that imitates the product's
UI but is rebuilt as fully animatable live HTML. The output is
`compositions/screen-script.html`, which the device-mockup recipe
embeds inside the iPhone/MacBook screen area.

This is the "fake real UI" capability that lets the skill produce
videos where on-screen content scales/responds to camera moves and
animates per the script — instead of pasting pixel-baked screenshots
that pixelate on close zoom.

Has a NO-LLM FALLBACK PATH (see --mode raw-screenshots) so the skill
still works without an Anthropic API key. The fallback cross-fades
between screenshots; the LLM path produces a real animatable UI.

Usage:
    # LLM mode (default)
    python3 synthesize_screen_ui.py product-brief.md \\
        --screenshots screenshots/*.png \\
        --out compositions/screen-script.html

    # Fallback (no API key needed)
    python3 synthesize_screen_ui.py product-brief.md \\
        --mode raw-screenshots \\
        --screenshots screenshots/*.png \\
        --out compositions/screen-script.html

Requires (LLM mode only):
    pip install anthropic Pillow

API key resolution: looks for ANTHROPIC_API_KEY env var, then
~/.anthropic/config.json (key: "api_key").
"""
import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

DEFAULT_MODEL = "claude-sonnet-4-5"


def load_anthropic_key() -> str:
    if "ANTHROPIC_API_KEY" in os.environ:
        return os.environ["ANTHROPIC_API_KEY"]
    cfg = Path.home() / ".anthropic" / "config.json"
    if cfg.exists():
        d = json.loads(cfg.read_text())
        return d.get("api_key", "")
    return ""


def encode_image(path: Path) -> dict:
    """Encode image as Anthropic content block."""
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "image/png")
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": data,
        },
    }


SYSTEM_PROMPT = """You are generating HTML+CSS that imitates an app UI for use as
animated content inside a 3D device mockup in a product explainer video.

Constraints:
1. Output ONLY a complete self-contained HTML file (no markdown fences, no commentary).
2. Single root element <div class="screen-root" id="screen-root">.
3. All styles inline in a single <style> block in <head>.
4. Use Inter font for sans and JetBrains Mono for code/terminal text.
5. Include a <script> block at the bottom that registers a GSAP timeline on
   window.__screenTimeline = gsap.timeline({ paused: true }) with animated
   beats matching the prompt. Use only deterministic timeline tweens — no
   Date.now, no Math.random, no setTimeout.
6. The composition is sized 100% × 100% — make content fluid, not fixed-pixel.
7. Match the aesthetic of the reference screenshots but rebuild as semantic HTML
   (not screenshot-baked). Type, layout, colors, spacing — all clean HTML+CSS.
8. Animate at least 4 distinct beats over ~15 seconds (typing, response, scroll,
   highlight, etc).
9. Output JetBrains Mono for any terminal/code text at 17px line-height 1.5.
10. Use `tl.set` only at or after each clip's data-start time — never `gsap.set` for
    elements that only exist later in the timeline.

The goal is a UI that can scale 0.86 → 1.14 (camera zoom) and remain crisp,
because it's real HTML not a baked screenshot."""


def synthesize_llm(brief_text: str, screenshot_paths: list, narrative: str, model: str = DEFAULT_MODEL) -> str:
    """LLM mode — Claude generates the HTML."""
    try:
        import anthropic
    except ImportError:
        print(
            "ERROR: anthropic SDK not installed. Run:\n"
            "  pip install --user anthropic\n"
            "OR use --mode raw-screenshots for the no-LLM fallback.",
            file=sys.stderr,
        )
        sys.exit(2)
    key = load_anthropic_key()
    if not key:
        print(
            "ERROR: no Anthropic API key (env ANTHROPIC_API_KEY or "
            "~/.anthropic/config.json). Use --mode raw-screenshots for "
            "the no-LLM fallback.",
            file=sys.stderr,
        )
        sys.exit(2)
    client = anthropic.Anthropic(api_key=key)

    content = []
    for p in screenshot_paths:
        if not p.exists():
            print(f"  WARN: screenshot {p} not found, skipping", file=sys.stderr)
            continue
        content.append(encode_image(p))
    content.append(
        {
            "type": "text",
            "text": (
                f"PRODUCT BRIEF:\n{brief_text}\n\n"
                f"NARRATIVE FOR THIS SCREEN (what the user 'does' across 15s):\n{narrative}\n\n"
                "Generate the HTML now."
            ),
        }
    )

    print(f"Calling {model}…", file=sys.stderr)
    t0 = time.time()
    resp = client.messages.create(
        model=model,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )
    print(f"  done in {time.time() - t0:.1f}s", file=sys.stderr)
    html = resp.content[0].text.strip()
    # Strip leading markdown fence if Claude added one against the rule
    if html.startswith("```"):
        html = html.split("```", 2)[1]
        if html.startswith("html"):
            html = html[4:]
        html = html.strip()
    return html


def synthesize_raw_screenshots(screenshot_paths: list, duration: float = 15.0) -> str:
    """Fallback — cross-fade between provided screenshots."""
    per_shot = duration / max(len(screenshot_paths), 1)
    img_tags = []
    fades = []
    for i, p in enumerate(screenshot_paths):
        rel = p.name
        img_tags.append(
            f'<img id="shot-{i}" src="{rel}" '
            f'style="position:absolute;inset:0;width:100%;height:100%;'
            f'object-fit:cover;opacity:{1 if i == 0 else 0};" />'
        )
        if i > 0:
            t = i * per_shot
            fades.append(
                f'      window.__screenTimeline.to("#shot-{i - 1}", '
                f'{{opacity: 0, duration: 0.5, ease: "power2.inOut"}}, {t:.2f});\n'
                f'      window.__screenTimeline.to("#shot-{i}", '
                f'{{opacity: 1, duration: 0.5, ease: "power2.inOut"}}, {t:.2f});'
            )
    return f"""<!doctype html>
<html>
<head>
<style>
  html, body {{ width: 100%; height: 100%; margin: 0; overflow: hidden; background: #000; }}
  .screen-root {{ position: relative; width: 100%; height: 100%; }}
</style>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
</head>
<body>
  <div class="screen-root" id="screen-root">
{chr(10).join("    " + tag for tag in img_tags)}
  </div>
  <script>
    window.__screenTimeline = gsap.timeline({{ paused: true }});
{chr(10).join(fades)}
  </script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brief", type=Path, help="Path to product-brief.md")
    ap.add_argument(
        "--screenshots",
        type=Path,
        nargs="*",
        default=[],
        help="Reference screenshot files (UI states the screen-script should emulate)",
    )
    ap.add_argument(
        "--narrative",
        default="user types a prompt, Claude responds, render bar fills to 100%, success message appears",
        help="What happens on the screen across the device-mockup duration",
    )
    ap.add_argument(
        "--mode",
        choices=["llm", "raw-screenshots"],
        default="llm",
        help="llm = Claude generates HTML (best quality); raw-screenshots = cross-fade fallback",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("compositions/screen-script.html"),
        help="Output path",
    )
    ap.add_argument("--model", default=DEFAULT_MODEL, help="Anthropic model")
    ap.add_argument(
        "--duration",
        type=float,
        default=15.0,
        help="(raw-screenshots mode) total cross-fade duration in seconds",
    )
    args = ap.parse_args()
    if not args.brief.exists():
        print(f"error: {args.brief} not found", file=sys.stderr)
        sys.exit(2)
    brief_text = args.brief.read_text()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    if args.mode == "llm":
        html = synthesize_llm(
            brief_text, args.screenshots, args.narrative, model=args.model
        )
    else:
        if not args.screenshots:
            print(
                "error: --mode raw-screenshots requires --screenshots",
                file=sys.stderr,
            )
            sys.exit(2)
        html = synthesize_raw_screenshots(args.screenshots, args.duration)

    args.out.write_text(html)
    print(f"✓ wrote {args.out} ({len(html)} bytes, mode={args.mode})")


if __name__ == "__main__":
    main()
