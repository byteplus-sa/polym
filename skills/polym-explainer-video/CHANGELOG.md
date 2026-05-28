# CHANGELOG — explainer-video skill

## Unreleased — post-Syncore feedback batch (2026-05-28)

Three structural fixes from real-world Syncore demo testing:

### Fix 1 — meta-output is opt-in, NOT default
The "QuickTime window playing the rendered video" beat was previously documented as the universal "signature finish". That was projection from v1-v5 self-demos. **For ordinary product launches it's distracting and project-specific.** Now:
- `templates/openai-product-demo.json` — the 19-26s slot is now a SECOND `device-mockup` segment (continued product walkthrough), not meta-output
- `references/meta-output-beat.md` — reframed top-to-bottom as opt-in for (a) video/media products, (b) recursive self-demos, (c) deliverable-artifact products
- All 5 style presets' "default scene recipe" updated to NOT include meta-output by default

### Fix 2 — language rule + 3-option approval gate
- `SKILL.md` top — new "Language rule": every user-facing prompt mirrors the user's conversation language. Internal references stay in English (for the model); user-visible options are in user's language.
- `SKILL.md` Phase 3 step 7 — approval gate is now an explicit 3-option AskUserQuestion: Approve / Specific changes / Stop. No more "proceeding on 'looks good'."

### Fix 3 — narrative arc is the first storyboard concern, not the last
- NEW `references/narrative-arc.md` — codifies the 5-beat structure + Syncore wrong-vs-right example
- `SKILL.md` Phase 3 step 0b — narrative arc establishment BEFORE drafting any UI scenes
- `references/storyboard-format.md` — `narrative` + `arc_map` top-level fields added
- `scripts/audit_storyboard.py` — new `check_narrative_arc()` (severity `severe`)

### Fix 3-expanded — 8 patterns from real STORYLINE.md
After a user shared a production-grade STORYLINE.md (Syncore reference), 7 more patterns were codified into the skill:

1. **Canon** — 3-5 specific entities (proper nouns) preserved across every frame. Top-level `canon` field. Severity: severe if < 3.
2. **Echo** — one canon entity recurs in 2+ frames as visual rhyme. Top-level `echo` field. Severity: warning if missing.
3. **Cast** — named protagonist + supporting cast. Top-level `cast` field. Severity: warning if protagonist is abstract ("user"/"viewer"/"developer").
4. **Frame-name keyword** — short UPPERCASE word per segment (`SUMMON`, `DETECT`). Per-segment `frame_name`. Severity: warning if missing.
5. **Per-frame narration** — every segment declares either `narration.line` + `cue_id` OR `narration.silent: true` + reason. Severity: warning if missing.
6. **Breather beat** — optional 6th beat between Magic and Promise. New `type: "breather"` value.
7. **Click chain** — UI products: top-level `click_chain` lists cursor clicks that trigger scene transitions, with timestamps. Auditor checks alignment within ±0.2s.
8. **Storyline-as-handoff doc** — generated storyboard.md must include 4 trailing sections (timeline / canon / what drives narrative / what's locked), not just the timeline table.

All 7 added as new fields in `references/storyboard-format.md`. All 7 audited by `audit_storyboard.py` with appropriate severities. Recipe `templates/openai-product-demo.json` updated to include all fields with REPLACE: placeholders that the auditor catches.

Result: Phase 3 now requires the model to think through cast / canon / echo / frame names / narration cues BEFORE drafting any segment. The "screen catalogue" failure mode is structurally impossible to render.

These fixes together address the v1 Syncore failure (UI screens with no story, meta-output beat that didn't serve the narrative, English prompts to a Chinese user, no production-grade structure for the model to follow).

---

## Unreleased — 12-PR refactor batch (2026-05-27)

This batch applies the 12-PR plan from `~/Desktop/Dev/explainer/SKILL_PRS.md` locally for testing. **Nothing has been pushed to GitHub yet** — review, run the smoke tests in `SMOKE_TEST.md`, then decide which PRs to extract and push.

Backup of the pre-refactor skill is at `~/Desktop/Dev/explainer/explainer-video.pre-refactor.bak`.

### Wave 1 — Quick wins (PRs 2, 9, 7, 11)

- **PR #2 — 60fps + drop 25fps + house easing**
  - NEW `references/motion-house-style.md` — non-negotiable easing/fps/timing rules
  - EDIT `references/production-techniques.md` §4 — replaces "normalize to 25fps" with "60fps end-to-end, interpolate A-roll UP not DOWN"
  - EDIT `scripts/compose_and_render.py` — passes `--fps 60 --quality high --workers 4` by default; `--fps` and `--quality` overrideable

- **PR #9 — Agent-agnostic defaults**
  - NEW `references/agent-list.md` — canonical brand info for 10 known AI coding agents (Claude Code, Codex, Cursor, OpenClaw, Cline, Aider, Hermes, Continue, Goose, Devin)
  - NEW `templates/agent-chip-row.html` — reusable opening pattern (icon + label tiles); CSS + GSAP snippet included
  - EDIT `SKILL.md` Onboarding intro — replaces "AI digital-human A-roll (you on camera)" with mode-aware language

- **PR #7 — Dead-air detector**
  - NEW `scripts/audit_storyboard.py` — flags dead-air windows ≥3s, segments missing beats, mode/A-roll mismatch, overflow-prone camera_path scales
  - EDIT `SKILL.md` Phase 3 — adds explicit "Run the storyboard auditor" sub-step before approval gate

- **PR #11 — Duration target + pacing audit**
  - Extends `audit_storyboard.py` with `PROFILE_TARGETS` (single-message 25-35s / few-features 40-55s / many-features 65-90s) and over-budget / under-budget flagging
  - EDIT `SKILL.md` Phase 3 — recommended-length table updated to compressed targets

### Wave 2 — Foundation (PRs 4, 1, 12)

- **PR #4 — Registry catalog awareness**
  - NEW `references/hyperframes-catalog.md` — curated ~15 high-value blocks/components organized by use case
  - NEW `scripts/fetch_registry.py` — fetches + caches the upstream registry.json (24h TTL); filter by type/tag/name
  - EDIT `scripts/compose_and_render.py` — `install_registry_blocks()` auto-runs `npx hyperframes add <name>` for any blocks referenced in storyboard

- **PR #1 — pure-broll mode + aspect_ratio**
  - EDIT `SKILL.md` Phase 1 — introduces `mode` choice: pure-broll-product-demo / aroll-broll-hybrid / aroll-only; auto-suggest rule
  - EDIT `SKILL.md` Phase 2 — skip Phase 2 entirely in pure-broll mode
  - EDIT `references/storyboard-format.md` — adds `mode`, `aspect_ratio`, `width`, `height`, `content_profile` to top-level schema
  - EDIT `references/broll-routing.md` — adds mode-aware routing + pure-broll default skeleton
  - EDIT `assets/hyperframes-template.html` — width/height/bg/font are now placeholders (was hardcoded 720×1280)
  - EDIT `scripts/compose_and_render.py` — `resolve_dimensions()` reads aspect_ratio; template substitution

- **PR #12 — Design + channel preflight**
  - EDIT `SKILL.md` Phase 1 — adds Q1 mode / Q2 visual identity / Q3 distribution channel
  - EDIT `SKILL.md` Phase 3 — surfaces design context in approval gate (channel/aspect/preset/mode)
  - NEW 5x `assets/style-presets/<name>/design.md` — openai-clean, anthropic-warm, linear-minimal, apple-keynote, brand-bold (each documents palette + typography + corners + motion + tone + recipe + "not for")
  - NEW `references/style-presets.md` — preset catalog + when-to-use guide
  - NEW `references/channel-aspect-ratios.md` — 11-channel × aspect-ratio × duration table with safe zones
  - EDIT `scripts/compose_and_render.py` — `load_style_preset()` reads design.md, applies bg/font tokens to template

### Wave 3 — Visual grammar (PRs 3, 6, 5)

- **PR #3 — caption-* components**
  - NEW `references/caption-components.md` — curated 4-component starter set (caption-kinetic-slam / weight-shift / gradient-fill / pill-karaoke) + selection guide per preset
  - EDIT `references/production-techniques.md` §1 — replaces deprecated PIL+ffmpeg pattern with caption-* registry components

- **PR #6 — Progressive camera-zoom + overflow validator**
  - Camera + transition fields already added to storyboard-format.md in Wave 2
  - NEW `scripts/validate_overflow.py` — post-render frame sampler; detects content within Npx of canvas edges (the case lint can't catch because layout-in-DOM is correct but CSS transform pushes content past viewport)
  - Overflow camera-path check added to `audit_storyboard.py` in Wave 1 (pre-render math-based estimate)

- **PR #5 — Device-mockup recipe + screen-UI synthesis**
  - NEW `templates/openai-product-demo.json` — canonical pure-broll recipe (32s, 1:1, openai-clean preset) with 5-segment structure
  - NEW `assets/macos-window-chrome.html` — reusable macOS window chrome for meta-output beat (or any "showing an app" scene)
  - NEW `references/screen-script-format.md` — how to script the in-device screen HTML; LLM-synthesis vs raw-screenshots fallback
  - NEW `scripts/synthesize_screen_ui.py` — Claude-powered HTML synthesis from product brief + screenshots; non-LLM fallback path included

### Wave 5 — Validation suite + auto-fix loop

A unified verification system that catches structural / asset / render-spec / audio problems automatically, with mechanical auto-fix for the subset that's safe to repair without semantic understanding.

- **NEW `scripts/check_overlap.py`** — detects (severe) same-track collisions where two clips share a track and overlap, (warning) unintended visible overlap >0.7s without a declared transition. Auto-fix recipes: `move_to_unique_track`, `tighten_overlap`.

- **NEW `scripts/check_assets.py`** — scans all composition HTML for src/href references, fails on missing files. Also ffprobes embedded `<video>` clips for keyframe density (severe if max-gap > 1.5s, warning if 1.0-1.5s). Auto-fix: `reencode_video` (overwrites with `-g 30 -keyint_min 30 -movflags +faststart`).

- **NEW `scripts/check_render_spec.py`** — post-render ffprobe; compares rendered resolution / fps / duration / codec against storyboard declaration. Auto-fix: `transcode_resolution`, `transcode_fps`. Duration mismatch is a warning with no auto-fix (means storyboard timing is wrong).

- **NEW `scripts/check_audio_levels.py`** — ffmpeg `volumedetect` on rendered MP4; verifies mean RMS in mode-target range (pure-broll: -22~-16 dB, hybrid: -20~-14 dB) and no clipping (max ≤ -1 dBFS). Auto-fix: `remix_volume` (in-place re-mux with adjusted gain).

- **NEW `scripts/verify.py`** — unified orchestrator. Runs every validator (audit_storyboard + check_overlap + check_assets + hyperframes lint/validate/inspect for pre; validate_overflow + check_render_spec + check_audio_levels for post). With `--auto-fix`, applies mechanical fixes and re-verifies up to `--max-iter` times (default 3). Exits with code 2 if severe issues remain after the loop.

- **EDIT `scripts/audit_storyboard.py`** — JSON output schema harmonized with the new validators (`{ok, findings: [{severity, code, message}], fixes: []}`) so verify.py can aggregate uniformly.

- **EDIT `scripts/compose_and_render.py`** — wires verify.py in at TWO points:
  1. **Pre-render** (after composition generation, before render): runs verify.py `--mode pre --auto-fix`. If severe issues remain, aborts unless `--force`. If auto-fix modified the storyboard, regenerates composition before render.
  2. **Post-render** (after MP4 produced): runs verify.py `--mode post --auto-fix`. Reports severe issues but doesn't block delivery.
  - New CLI flags: `--no-auto-fix`, `--verify-max-iter N`, `--force`.

- **EDIT `SKILL.md`** — Phase 3 step 6 now references the unified `verify.py` instead of just `audit_storyboard.py`. Phase 4 step 7 documents the post-render auto-verify.

#### What auto-fix repairs (safe)

- Camera scales that overflow canvas → capped to safe-max (~1.10× content)
- Embedded video keyframe density → re-encoded with `-g 30`
- Audio mean / clipping → in-place re-mux with gain adjustment
- Same-track collisions → segment moved to next available track
- Unintended overlap → earlier segment duration shrunk

#### What auto-fix won't touch (surfaced for human/LLM)

- Dead air windows — needs semantic decision (add a beat? shorten segment? cut to next?)
- Over-budget duration — needs content cuts
- Adjacent duplicate segments — needs intent change
- Missing assets — the file has to be provided
- Text contrast — color space changes are too risky for a mechanical fix
- A-roll/mode mismatch — needs storyboard restructuring

### Wave 4 — Signature (PRs 8, 10)

- **PR #8 — Meta-output multi-shot beat**
  - NEW `references/meta-output-beat.md` — documents the "QuickTime window with multi-shot brand preview" pattern; synthetic (default) vs recursive-video (two-pass) strategies; keyframe-density gotcha
  - EDIT `SKILL.md` Phase 4 step 6 — adds optional two-pass render step for recursive strategy
  - The `meta-output` segment type with `shots[]` array is documented in storyboard-format.md (Wave 2) + openai-product-demo.json (Wave 3)

- **PR #10 — Beat-sync onset detection**
  - NEW `scripts/beat_align.py` — librosa-based onset detection + ±150ms snap of transition/beat times to nearest music onset
  - EDIT `SKILL.md` Phase 4 — adds optional step 4b (between music gen and assemble) for beat-align; falls back silently if librosa not installed
  - EDIT `references/storyboard-format.md` — adds per-segment `snap_to_beat: true/false` field

### What was NOT changed

- `references/seedance-api.md` — A-roll generation API docs unchanged (still authoritative for hybrid + aroll-only modes)
- `references/seedream-api.md` — portrait restyle unchanged
- `references/volcengine-music-api.md` — music gen unchanged (still works for both old + new flow)
- `references/cost-rates.md` — token cost reference unchanged
- `references/lark-upload-guide.md` — upload helper unchanged
- `references/reference-video-analysis.md` — style extraction utility unchanged
- `references/hook-patterns.md` — hook templates unchanged (still relevant for A-roll flows)
- `assets/package.json` / `assets/hyperframes.json` / `assets/meta.json` — npm + hyperframes config unchanged
- `scripts/preflight.py` / `parse_inputs.py` / `estimate_cost.py` / `analyze_reference_video.py` / `upload_to_lark.py` — auxiliary scripts unchanged

## File count summary

| Type | Count |
|---|---:|
| New files | 16 |
| Edited files | 7 |
| Total touched | 23 |

| Wave | New | Edited |
|---|---:|---:|
| 1 (PRs 2, 9, 7, 11) | 4 | 3 |
| 2 (PRs 4, 1, 12) | 9 | 4 |
| 3 (PRs 3, 6, 5) | 6 | 1 |
| 4 (PRs 8, 10) | 2 | 1 |
| 5 (Validation + auto-fix) | 5 | 2 |
| CHANGELOG + SMOKE_TEST | 2 | 0 |

(Some files appear in multiple waves' edit counts — Wave 1's SKILL.md edits got extended in Waves 2-4 as new sections came online.)

## How to test

See `SMOKE_TEST.md` for a per-wave test plan. The quickest end-to-end smoke is:
1. Trigger the skill ("Make an explainer video about <topic>")
2. Verify Phase 1 asks the 3 preflight questions (mode / style / channel)
3. Verify Phase 3 surfaces the design context + runs `audit_storyboard.py`
4. Verify Phase 4 renders at 60fps with the chosen aspect ratio
5. Verify the rendered MP4 has no overflow warnings from `validate_overflow.py`

## Rollback

If anything breaks, restore from backup:

```bash
rm -rf ~/.claude/skills/explainer-video
cp -r ~/Desktop/Dev/explainer/explainer-video.pre-refactor.bak ~/.claude/skills/explainer-video
```
