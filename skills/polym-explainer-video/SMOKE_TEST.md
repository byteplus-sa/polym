# Smoke test guide — explainer-video skill (post 12-PR refactor)

Quick tests to verify each wave works before deciding which PRs to push to GitHub.

## Setup

```bash
# Confirm files exist
ls ~/.claude/skills/polym-explainer-video/scripts/audit_storyboard.py
ls ~/.claude/skills/polym-explainer-video/scripts/fetch_registry.py
ls ~/.claude/skills/polym-explainer-video/scripts/validate_overflow.py
ls ~/.claude/skills/polym-explainer-video/scripts/synthesize_screen_ui.py
ls ~/.claude/skills/polym-explainer-video/scripts/beat_align.py
ls ~/.claude/skills/polym-explainer-video/templates/agent-chip-row.html
ls ~/.claude/skills/polym-explainer-video/templates/openai-product-demo.json
ls ~/.claude/skills/polym-explainer-video/assets/style-presets/openai-clean/design.md
ls ~/.claude/skills/polym-explainer-video/assets/macos-window-chrome.html
```

All 9 should exist after the refactor.

## Wave 1 tests (PRs 2, 9, 7, 11)

### PR #2 — render at 60fps

```bash
python3 ~/.claude/skills/polym-explainer-video/scripts/compose_and_render.py --help | grep -A1 fps
```

Expected: `--fps` defaults to 60.

### PR #7 + #11 — storyboard auditor

Make a tiny storyboard that's intentionally bad and run the auditor:

```bash
cat > /tmp/bad-storyboard.json << 'EOF'
{
  "mode": "pure-broll-product-demo",
  "style_preset": "openai-clean",
  "channel": "x",
  "aspect_ratio": "1:1",
  "content_profile": "single-message",
  "total_duration": 60,
  "segments": [
    {"id": "open", "type": "title-card", "tool": "hyperframes", "start": 0, "duration": 4, "intent": "Hello"},
    {"id": "long-dead", "type": "device-mockup", "tool": "hyperframes", "start": 4, "duration": 50, "intent": "lots of empty time", "beats": [{"at": 5, "name": "one"}]},
    {"id": "aroll-violation", "type": "a-roll", "tool": "seedance", "start": 54, "duration": 6, "intent": "shouldn't be here in pure-broll mode"}
  ]
}
EOF

python3 ~/.claude/skills/polym-explainer-video/scripts/audit_storyboard.py /tmp/bad-storyboard.json
```

Expected: warnings about (a) total 60s over single-message target by >30%, (b) dead air in long-dead segment, (c) A-roll in pure-broll mode.

### PR #9 — agent-list reference

```bash
cat ~/.claude/skills/polym-explainer-video/references/agent-list.md | grep -c "^|"
```

Expected: ~12+ rows in the agent table.

## Wave 2 tests (PRs 4, 1, 12)

### PR #4 — registry fetch + cache

```bash
python3 ~/.claude/skills/polym-explainer-video/scripts/fetch_registry.py --type block | head -30
```

Expected: prints registry items grouped by type; cache lands at `~/.explainer-video/registry-cache.json`.

```bash
python3 ~/.claude/skills/polym-explainer-video/scripts/fetch_registry.py --name caption
```

Expected: just caption-* items.

### PR #1 + #12 — preflight in actual skill invocation

This is the integration test. Trigger the skill via Claude Code:

> "Make me a 30-second 1:1 video for X about <some product>, openai-clean style."

Expected behavior in Claude's response:
- Phase 1 asks the 3 preflight questions (or absorbs the answers from the prompt)
- Storyboard.json contains `mode`, `style_preset`, `channel`, `aspect_ratio` top-level fields
- Phase 3 shows the design context line ("This storyboard targets X at 1:1 using openai-clean...")
- The Phase 3 cost estimate omits Seedance line items (pure-broll mode)

### PR #12 — style presets exist

```bash
for p in openai-clean anthropic-warm linear-minimal apple-keynote brand-bold; do
  echo "--- $p ---"
  grep -E "^bg_primary|^accent" ~/.claude/skills/polym-explainer-video/assets/style-presets/$p/design.md
done
```

Expected: each preset's design.md has bg_primary + accent declared.

## Wave 3 tests (PRs 3, 6, 5)

### PR #3 — caption components doc

```bash
grep -c "caption-" ~/.claude/skills/polym-explainer-video/references/caption-components.md
```

Expected: 15+ caption-* references (4 starter set + 12 others).

### PR #6 — overflow validator

Use an existing rendered MP4 (e.g. the v4 demo):

```bash
python3 ~/.claude/skills/polym-explainer-video/scripts/validate_overflow.py \
  /Users/bojsun/Downloads/bobyte-explainer-demo-v4.mp4 \
  --at 5,10,15,20,25,30
```

Expected: outputs OK or FAIL with timestamped edge intrusions. (The v4 demo will FAIL with 8px margin warnings — that's known and documented.)

### PR #5 — recipe template + screen synth script exists

```bash
cat ~/.claude/skills/polym-explainer-video/templates/openai-product-demo.json | python3 -m json.tool > /dev/null && echo "valid JSON"
python3 ~/.claude/skills/polym-explainer-video/scripts/synthesize_screen_ui.py --help | head -10
```

Expected: JSON valid; help text shows --mode llm / raw-screenshots.

## Wave 4 tests (PRs 8, 10)

### PR #8 — meta-output beat doc

```bash
grep -E "^## " ~/.claude/skills/polym-explainer-video/references/meta-output-beat.md
```

Expected: sections on multi-shot, two strategies, QT chrome, per-preset, when-not-to-use.

### PR #10 — beat-sync dry-run

```bash
# librosa is heavy; install only if you want to actually test
# pip install --user librosa numpy soundfile

python3 ~/.claude/skills/polym-explainer-video/scripts/beat_align.py --help | head -10
```

Expected: help text. If you have a storyboard.json + music_bed.m4a from a previous render:

```bash
python3 ~/.claude/skills/polym-explainer-video/scripts/beat_align.py \
  storyboard.json assets/music_bed.m4a --dry-run
```

Expected: lists snapped timings (or "librosa not installed; skipping" — graceful).

## Wave 5 tests (validation suite + auto-fix loop)

### Individual validators on the canonical recipe

```bash
cd ~/.claude/skills/polym-explainer-video
python3 scripts/audit_storyboard.py templates/openai-product-demo.json   # 0 warnings
python3 scripts/check_overlap.py templates/openai-product-demo.json       # 0 findings
python3 scripts/check_assets.py --project-root templates                  # skipped (no index.html)
```

### verify.py orchestrator — clean storyboard

```bash
python3 scripts/verify.py templates/openai-product-demo.json --mode pre
```

Expected: `severe: 0  warnings: 0  auto-fixable: 0`

### Auto-fix loop — deliberately broken storyboard

Make a broken storyboard with overflow + track collision:

```bash
cp ~/.claude/skills/polym-explainer-video/templates/openai-product-demo.json /tmp/broken-sb.json
python3 - << 'EOF'
import json
sb = json.load(open('/tmp/broken-sb.json'))
sb['segments'][1]['camera_path'][-1]['scale'] = 1.45            # overflow
sb['segments'][1]['track_index'] = 2; sb['segments'][1]['duration'] = 20  # collision
sb['segments'][2]['track_index'] = 2
json.dump(sb, open('/tmp/broken-sb.json', 'w'), indent=2)
EOF

# Without auto-fix — should find 1 severe + 2 warnings
python3 scripts/verify.py /tmp/broken-sb.json --mode pre

# With auto-fix — should converge to 0 severe (1 warning remains: dead air, semantic)
python3 scripts/verify.py /tmp/broken-sb.json --mode pre --auto-fix
```

Expected with `--auto-fix`:
```
iteration 1:
  applies cap_camera_scale + move_to_unique_track
iteration 2:
  severe: 0  warnings: 1
  · audit_storyboard dead_air: <a remaining semantic issue>
```

### Post-render validators on an existing MP4

Use any rendered MP4 from earlier iterations:

```bash
python3 scripts/check_render_spec.py \
  templates/openai-product-demo.json \
  /Users/bojsun/Downloads/bobyte-explainer-demo-v4.mp4

python3 scripts/check_audio_levels.py \
  templates/openai-product-demo.json \
  /Users/bojsun/Downloads/bobyte-explainer-demo-v4.mp4
```

Expected: 0 findings (v4 matches the recipe's 1440×1440/60fps/32s spec, audio in -22 to -16 dB target range).

### Integrated pipeline test

When you next run the full skill, `compose_and_render.py` will:
1. Generate composition
2. Run `verify.py --mode pre --auto-fix` → potentially modify storyboard and regenerate composition
3. Render
4. Run `verify.py --mode post --auto-fix` → potentially re-mux audio gain in place
5. Report final status

If you want to opt out: pass `--no-auto-fix` to verify only without repairing, or `--force` to render even when severe issues are present.

## Storyline patterns test (8 patterns from STORYLINE.md)

The auditor enforces 8 narrative patterns. To verify they all trip correctly:

```bash
# Bare storyboard (no narrative metadata) → should fail with 5+ severe findings
cat > /tmp/bare.json <<'EOF'
{ "mode": "pure-broll-product-demo", "aspect_ratio": "1:1",
  "total_duration": 30, "segments": [
    {"id": "s1", "start": 0, "duration": 30, "type": "device-mockup", "tool": "hyperframes"}
  ]}
EOF
python3 ~/.claude/skills/polym-explainer-video/scripts/audit_storyboard.py /tmp/bare.json
```

Expected: warnings about missing narrative / canon / cast / echo / narration / frame_name. The first 2 are severe (block render).

```bash
# Recipe template with REPLACE: placeholders still in → should fail
python3 ~/.claude/skills/polym-explainer-video/scripts/audit_storyboard.py \
  ~/.claude/skills/polym-explainer-video/templates/openai-product-demo.json
```

Expected: 2 warnings — narrative REPLACE: placeholders + canon empty. Both severe.

## End-to-end (the full test)

The most useful test: actually trigger the skill on a real input and verify the new flow.

```text
You: "Make a 30s 1:1 X video about <some product>"

Expected Claude response:
  Phase 1 Intake:
    - reads input
    - shows product-brief
    Preflight:
      Q1 mode → auto-suggests pure-broll
      Q2 style → asks (or auto-suggests openai-clean based on context)
      Q3 channel → infers x / 1:1 / 1440×1440 from the input prompt
  Phase 2: skipped (pure-broll mode)
  Phase 3:
    - shows design context line first
    - shows storyboard
    - runs audit_storyboard.py — should be 0 warnings on a clean draft
    - shows cost (just music if enabled, no Seedance)
    - WAITS FOR APPROVAL
  Phase 4 (after approval):
    - installs registry blocks per storyboard
    - generates index.html at 1440×1440 with openai-clean tokens
    - renders at 60fps
    - generates music (if enabled)
    - assembles
  Phase 5: delivers MP4
```

If any of those steps don't happen as expected, that's a bug to investigate. The most likely failure: Claude doesn't read motion-house-style.md / style-presets.md before authoring the composition, producing motion that violates the rules. If that happens, the fix is to make SKILL.md Phase 4 reference those files more aggressively (already does, but may need stronger wording).

## Rollback

Pre-refactor backup:

```bash
rm -rf ~/.claude/skills/polym-explainer-video
cp -r ~/Desktop/Dev/explainer/explainer-video.pre-refactor.bak ~/.claude/skills/polym-explainer-video
```

## Reporting back

After running the tests, if you want to push specific PRs to the GitHub repo:

1. Identify which PRs work cleanly end-to-end
2. Extract their diffs from the changes documented in `CHANGELOG.md`
3. Open a PR per-PR (or grouped per-wave) against `github.com/encircleacity2/bobyte-explainer`

The 4 lowest-risk PRs to ship first (Wave 1) require zero coordination — pick any 1 and push as a standalone PR to validate the workflow.
