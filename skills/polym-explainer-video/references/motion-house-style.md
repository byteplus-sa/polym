# Motion house style — non-negotiable rules

These rules apply to **every** B-roll composition this skill generates. They exist because the difference between "feels cheap" and "feels premium" in product video is almost entirely motion craft — the same content with bad easings looks amateur; with these rules it looks like an Apple/OpenAI launch.

When you author or modify any GSAP timeline, apply these defaults unless the design preset (`assets/style-presets/<name>/design.md`) explicitly overrides.

---

## 1. Frame rate: 60fps default

Always render at **60fps `--quality high`**. The old skill default was 30fps with a 25fps concat downsample — both are killed in this version.

`scripts/compose_and_render.py` passes `--fps 60 --quality high` automatically. Do not override unless the user explicitly requests a slower rate for file-size reasons (e.g. "I need this under 5MB").

A-roll Seedance clips usually return at 24fps. Pre-process with `ffmpeg -vf "fps=60"` before concat — frame-interpolate up, never sample down.

## 2. Forbidden: `linear` easing

Linear movement reads as mechanical. Replace every `ease: "linear"` or missing-ease tween with one of the curves in the cheat sheet below.

The only exception: continuous background drift (liquid blobs, slow camera pans) that runs across the entire scene. Use `sine.inOut` for those.

## 3. Easing cheat sheet (use these, period)

| Intent | Ease | Duration | Notes |
|---|---|---|---|
| Element enters (text, card, image) | `power3.out` | 0.5–0.7s | Default for ~80% of entrances |
| Element with playful character | `back.out(1.5)` to `back.out(1.7)` | 0.5–0.65s | Springy overshoot; great for chips, badges, logos |
| Element with snap/impact | `back.out(2.2)` | 0.22–0.3s | High-energy kinetic text |
| Camera move (zoom, pan) | `power1.inOut` or `power2.inOut` | 2–5s | Slow, breathing |
| Slow continuous drift | `sine.inOut` | 5–35s | Backgrounds, blobs, particles |
| Transient highlight | `expo.out` | 0.2–0.35s | Caret blinks, snap-focus |
| Pre-cut emphasis | `expo.inOut` | 0.6–0.9s | Build then commit; great for transitions |
| Exit (final scene only) | `power2.inOut` | 0.4–0.6s | See rule 5 |

## 4. Duration windows

- Entrance tweens: **0.4–0.9s**. Faster = jittery, slower = sluggish.
- Holds (no motion): **min 0.6s, max 2.5s**. Any longer = dead air (see PR #7's audit).
- Camera moves: **2–5s** per phase. Slow continuous is fine; abrupt zooms are not.
- Cross-fades between scenes: **0.5–0.7s** with `power2.inOut`.

## 5. Transform always, opacity never alone

Every appearance / disappearance must combine `opacity` change with a `transform` (`x`, `y`, `scale`, `rotation`). Opacity-only fades look hollow.

```js
// WRONG — opacity only
tl.fromTo("#card", { opacity: 0 }, { opacity: 1, duration: 0.5 });

// RIGHT — opacity + transform
tl.fromTo("#card",
  { opacity: 0, y: 24, scale: 0.96 },
  { opacity: 1, y: 0, scale: 1, duration: 0.55, ease: "power3.out" });
```

## 6. Exit animations: final scene only

Per the hyperframes skill's scene-transitions rule: do NOT use `tl.to(..., { opacity: 0 })` to fade scene content before a transition fires. The transition IS the exit. The outgoing scene must be fully visible at the moment the transition starts.

The only exception is the FINAL scene of the composition (typically a wordmark / logo-outro), which may fade to black or fade to background at the very end.

In practice for this skill: use overlapping clip durations and let the next scene's entrance cover the previous one. If you must explicitly fade out a scene before the next starts (a stylistic choice), document why in a code comment.

## 7. Stagger discipline

When animating a group (chips, list items, words):
- Stagger interval: **0.06–0.10s** between siblings
- 4+ items: vary the easing across the group (alternate `power3.out` and `back.out(1.5)`)
- Don't use stagger > 0.15s for visible groups — it feels slow

## 8. Continuous drift for "alive" backgrounds

Static backgrounds read as flat. Add at least one of:
- A liquid-blob drift (3+ blurred radial gradients moving slowly via `sine.inOut` over the full scene duration)
- A subtle camera push-in (1.0 → 1.05 over 20s with `power1.inOut`)
- Subtle particle drift (1px white dots at low opacity, randomized starting positions, moving over 8-15s)

Never have zero motion in a static B-roll scene for >2s.

---

## Quick checklist before render

- [ ] `--fps 60 --quality high` on render command
- [ ] Zero `linear` easings (grep your composition)
- [ ] Every entrance tween combines opacity + transform
- [ ] Holds of any element are 0.6–2.5s
- [ ] At most one exit-fade tween per scene; final scene only
- [ ] No background is fully static for >2s

If any fails, fix before rendering. The render takes minutes; a re-render after motion polish costs you those minutes per round.
