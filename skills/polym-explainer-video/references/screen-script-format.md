# Screen-script format — content inside the device screen (PR #5)

When the storyboard's `device-mockup` segment uses `vfx-iphone-device` (or a CSS-drawn MacBook frame), the **content shown on the screen** is a separate, scripted HTML artifact: `compositions/screen-script.html`.

This file lives inside the device's screen area and animates on its own sub-timeline that gets composed with the parent camera timeline. It's how you make a device shot feel "alive" — the device camera-moves slowly while the on-screen content evolves quickly.

## Why this matters

In the OpenAI/Apple/Linear product videos this skill emulates, the device frame typically:
1. Pulls back wide (small device on background)
2. Pushes in over 20-30s while…
3. …the on-screen UI rapidly types prompts, shows AI responses, opens menus, runs commands.

If the on-screen content is a static image, the long device shot dies. The screen MUST animate — that's the entire point of the device-mockup recipe.

## Two implementation modes

### Mode A — synthesized HTML (PR #5 scripts/synthesize_screen_ui.py)

Best for: showing an app UI that doesn't exist yet or that you want stylized.

Workflow:
1. Phase 4 calls `synthesize_screen_ui.py product-brief.md screenshots/*.png`
2. The script prompts Claude (Anthropic SDK) to generate semantically faithful HTML+CSS that mimics the user-supplied UI but is rebuilt as live HTML
3. Output: `compositions/screen-script.html` with placeholder timing markers
4. Composition authoring fills in the GSAP timeline that animates the screen contents

Pros: scales/responds to camera moves; fully animatable; clean typography
Cons: requires Anthropic API key; one-shot LLM cost (~$0.10-0.30)

### Mode B — raw screenshots (no-LLM fallback)

Best for: when you can't / won't use the LLM mode, or when the UI is too custom to re-synthesize.

Workflow:
1. User provides a sequence of screenshots representing UI states (e.g. `state-1.png`, `state-2.png`, `state-3.png`)
2. The screen-script.html cross-fades between them on a sub-timeline
3. Camera moves still work but the screenshots can't react to scale (they pixelate at high zoom)

Pros: works without API key; faithful to real UI
Cons: pixelates on close zoom; can't animate the screen text itself; harder to make "type" effects feel real

## Screen-script.html structure

```html
<!doctype html>
<html>
  <head>
    <style>
      /* Reset + screen-sized container */
      html, body { width: 100%; height: 100%; margin: 0; overflow: hidden; background: #0e0e12; }
      .screen-root { position: relative; width: 100%; height: 100%; }
      /* Your UI styles here */
    </style>
  </head>
  <body>
    <div class="screen-root" id="screen-root">
      <!-- Your synthesized UI markup -->
    </div>

    <script>
      // Sub-timeline registered on window.__screenTimeline so the parent
      // composition can compose it into the main timeline at known offsets.
      window.__screenTimeline = gsap.timeline({ paused: true });

      // Type-effect, fade-in, scroll-up, etc — same hyperframes deterministic rules.
      window.__screenTimeline.fromTo("#prompt-text",
        { text: "" },
        { duration: 2.4, text: { value: "Make a launch explainer for ByteDance Seed 2.0" }, ease: "none" },
        2.0);
      // ...more beats...
    </script>
  </body>
</html>
```

The parent composition references this via `data-composition-src="compositions/screen-script.html"` (standard HyperFrames sub-composition wiring) OR via the `vfx-iphone-device` block's HTML-in-canvas slot.

## Timing alignment

The screen-script's sub-timeline runs in **screen-local time** — `0s` is when the screen first becomes visible in the parent timeline. Map to parent like:

```js
// In parent composition:
const screenTl = window.__screenTimeline;
// Compose at parent t=4.5s (when device enters)
window.__timelines["main"].add(screenTl, 4.5);
```

## Beats schema

For consistency with the `audit_storyboard.py` dead-air check (PR #7), each scripted screen action should declare a `beats[]` entry in the parent storyboard's `device-mockup` segment:

```json
{
  "id": "device-shot",
  "duration": 15.5,
  "screen_content_html": "compositions/screen-script.html",
  "beats": [
    {"at": 0.5, "name": "macbook_enter"},
    {"at": 2.0, "name": "typing_start"},
    {"at": 5.0, "name": "claude_responds"},
    ...
  ]
}
```

The auditor uses `beats[]` to verify no 3+ second gaps within the segment.

## Anti-patterns

- **Don't** make the screen-script async — HyperFrames timelines must be built synchronously
- **Don't** use real `<video>` inside the screen content — too much complexity. If you need a "video playing on the laptop", that's the meta-output beat (PR #8), not the device-mockup beat
- **Don't** mix Mode A and Mode B in the same screen-script — pick one tech
- **Don't** put critical text in the corners of the screen — when the device is at small scale (camera pulled back), corners are nearly unreadable

## Per-style-preset recommendations

| Preset | Typical screen content |
|---|---|
| `openai-clean` | Claude Code TUI / terminal interactions |
| `anthropic-warm` | Editor/IDE with thoughtful code, sparkle accents |
| `linear-minimal` | Dashboard with metrics, dark UI |
| `apple-keynote` | Single feature in focus (camera viewfinder, ML demo screen) |
| `brand-bold` | Brand product UI screenshot (bold and brand-colored) |
