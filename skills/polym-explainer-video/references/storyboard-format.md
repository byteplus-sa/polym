# Storyboard format specification

The storyboard is the artifact approved before any paid generation runs (Phase 3 gate).
It must be complete, unambiguous, and reviewable by a non-technical user.

## File location

Working directory: `storyboard.md` (human-readable) and optionally `storyboard.json`
(machine-readable for `compose_and_render.py`). Keep them in sync.

## Top-level storyboard.json schema (post PR #1 + #4 + #6 + #12)

```jsonc
{
  // === From Phase 1 preflight (PR #1 + #12) ===
  "mode": "pure-broll-product-demo",     // | "aroll-broll-hybrid" | "aroll-only"
  "style_preset": "openai-clean",        // one of 5 built-ins, or "custom"
  "style_overrides": {                   // optional; per-task tweaks
    "accent": "#FF6B35"
  },
  "channel": "x",                        // x | linkedin | tiktok | youtube | website | multi
  "aspect_ratio": "1:1",                 // 1:1 | 9:16 | 16:9
  "width": 1440,                          // derived from aspect_ratio
  "height": 1440,

  // === Content shape ===
  "content_profile": "single-message",   // single-message | few-features | many-features
  "total_duration": 32.0,
  "agent_list": ["claude", "codex"],     // optional; for agent-row openings (PR #9)

  // === Narrative (CRITICAL — see references/narrative-arc.md) ===
  "narrative": {
    "protagonist": "Founder who lives meeting-to-meeting",
    "problem": "Post-meeting commitments die between calendar and inbox",
    "moment_of_magic": "Watching Syncore lift a 4-day-old commitment from a recording and pre-draft the message",
    "memorable_line": "Made for the work between meetings.",
    "cta": "syncore.app"
  },
  "arc_map": {
    "hook":    ["frame-summon"],
    "tension": ["frame-alongside"],
    "reveal":  ["frame-detect"],
    "magic":   ["frame-file", "frame-handoff", "frame-kept"],
    "breather": ["frame-later"],   // optional 6th beat
    "promise": ["frame-end"]
  },

  // === Cast (Pattern 3) — named protagonist + supporting cast ===
  "cast": {
    "protagonist": {
      "name": "Erica",
      "role": "Engineering lead",
      "affiliation": "her own startup",
      "motivation": "Doesn't want to forget what she said in meetings"
    },
    "supporting": [
      { "name": "David Chen", "role": "PM", "affiliation": "Vertex Labs" },
      { "name": "Sam",        "role": "engineer", "affiliation": "Vertex Labs" },
      { "name": "Priya",      "role": "designer", "affiliation": "Vertex Labs" }
    ]
  },

  // === Canon (Pattern 1) — 3-5 specific entities preserved across every frame ===
  "canon": {
    "meeting":         "Vertex Labs sync",
    "other_party":     "David Chen (Vertex Labs · david@vertexlabs.co)",
    "central_quote":   "I'll send you the rollout setup guide by Thursday.",
    "attached_doc":    "Notion — Vertex onboarding · rollout SOP",
    "background_promises": [
      "Maya Singh / Acme — pricing breakdown",
      "Tom Riley / Northwind — confirm meeting slot",
      "Jen Park / Helix — review proposal"
    ]
  },

  // === Echo (Pattern 2) — artifact that recurs across 2+ frames as visual rhyme ===
  "echo": [
    {
      "artifact": "central_quote",
      "appears_in": ["frame-detect", "frame-handoff", "frame-kept"],
      "treatment": "italic serif quote, same typography across all 3 occurrences"
    }
  ],

  // === Click chain (Pattern 7) — UI products only ===
  "click_chain": [
    { "at": 2.55, "button": "Start meeting notes", "in_frame": "frame-summon",   "triggers": "frame-alongside" },
    { "at": 17.35, "button": "Draft",              "in_frame": "frame-file",     "triggers": "frame-handoff" },
    { "at": 30.30, "button": "Send (prompt)",      "in_frame": "frame-handoff",  "triggers": "frame-kept" },
    { "at": 38.55, "button": "Send (email)",       "in_frame": "frame-kept",     "triggers": "frame-end" }
  ],

  // === Segments (per-segment fields below) ===
  "segments": [ ... ]
}
```

## Per-segment fields

```jsonc
{
  "id": "frame-detect",
  "frame_name": "DETECT",                // Pattern 4 — short UPPERCASE keyword
  "start": 7.45,
  "duration": 6.0,
  "type": "device-mockup",               // title-card | device-mockup | wordmark | data-viz | meta-output | breather | a-roll | b-roll-video
  "tool": "hyperframes",

  // === Pattern 5 — Narration cue (REQUIRED — either this OR silent:true) ===
  "narration": {
    "cue_id": "03 · DETECT",
    "line": "Spots commitments as you make them. No tagging required.",
    "silent": false
  },
  // OR, for silent frames (breather, end card, etc):
  // "narration": { "silent": true, "reason": "the breather is the point" }

  // === Pattern 7 — Click chain (UI products only) ===
  "click_triggers_next": false,          // if true, declare click time + next frame in top-level click_chain

  // === Canon reference (Pattern 1) — which canon entities appear in this frame ===
  "canon_used": ["meeting", "other_party", "central_quote"],

  // === Existing fields ===
  "block": "vfx-iphone-device",
  "block_params": { "screen_content_html": "compositions/screen-script.html" },
  "camera_path": [
    {"at": 0.0, "scale": 0.86},
    {"at": 5.0, "scale": 1.04}
  ],
  "transition_in": "cross-fade",
  "beats": [
    {"at": 0.5, "name": "meeting_scales_up"},
    {"at": 2.0, "name": "quote_highlighted"},
    {"at": 4.0, "name": "promise_chip_materializes"}
  ],
  "snap_to_beat": true,

  "intent": "Erica's promise to David gets highlighted in transcript; PROMISE chip materializes",
  "script": "...",                       // A-roll only
  "caption": "...",
  "caption_start": 0.3,
  "caption_duration": 4.5
}
```

---

## storyboard.md format

```markdown
# Storyboard — <product name>

## Recommended length: 90s
**Rationale:** <why — content profile, number of features/skills to cover>

## Timeline

| # | Time | Type | Tool | Content | Spoken / VO |
|---|------|------|------|---------|-------------|
| 1 | 0–5s   | B-roll | HyperFrames | Kinetic-typography hook | — |
| 2 | 5–12s  | A-roll | Seedance 2.0 | Intro to camera | "Every SA juggles Lark, meetings, dashboards…" |
| 3 | 12–16s | B-roll | HyperFrames | Install scene | — |
| 4 | 16–86s | B-roll | HyperFrames | 7 skill demos, 10s each | — |
| 5 | 86–91s | A-roll | Seedance 2.0 | Closing CTA to camera | "Seven skills, one install. Get it on GitHub." |
| 6 | 91–96s | B-roll | HyperFrames | Brand reveal | — |

## Segment details

### Segment 1 (B-roll HyperFrames, 0–5s) — kinetic-typography hook
- **Why this tool:** rhythmic word animation needs precise type control — HyperFrames.
- **Spec:** chaos words punch-flash in sequence, then resolve to the POLYM wordmark + tagline.

### Segment 2 (A-roll Seedance 2.0, 5–12s)
- **Mode:** r2v (reference video → voice + facial motion) or image+text — see SKILL.md.
- **Script:** "Every SA juggles Lark, meetings, dashboards and wikis. Polym does the heavy lifting."
- **Tone:** warm, confident, direct to camera.
- **Note:** even in r2v mode, put the script in the text prompt so the spoken words are controlled.

### Segment 4 (B-roll HyperFrames, 16–86s) — skill demos
- **Why this tool:** typed-prompt + result + deliverable cards need exact UI mockups — HyperFrames.
- **Spec:** per skill (~10s): title → typed prompt → agent runs → result → deliverable doc card.

### Segment 5 (A-roll Seedance 2.0, 86–91s) — closing CTA
- **Script:** "Seven skills. One install. Polym — your SA team's polymath. Get it on GitHub."

## Cost estimate

| Item | Quantity | Cost |
|------|----------|------|
| Seedance A-roll | 2 clips (~12s) | <tokens> |
| HyperFrames B-roll | N segments | $0 |
| Volcengine music | 1 track | <small> |
| **Total** |  | **<tokens> + small** |

## Approval

**Status:** ⏸ Awaiting user approval — respond `approve` / `change <segment>` / `restart`.
```

---

## Segment field rules

| Segment type | Tool | Notes |
|---|---|---|
| A-roll | `seedance-2.0` | Talking-head. Always carries a spoken `script`. Keep each clip 5–10s. Typically only 2 per video (hook + CTA). |
| B-roll | `hyperframes` | Typographic / data / demo scenes. Free, local render. The default for B-roll. |
| B-roll | `seedance-2.0` | Only for non-person cinematic / atmospheric shots. |

There is **one** A-roll tool: Seedance 2.0. Do not mix A-roll tools.

---

## Validation checklist

Before presenting to the user, verify:

- [ ] Segment durations sum to the stated total; no timeline gaps.
- [ ] A-roll segments are 5–10s each; the spoken script fits the duration (~2 words/sec).
- [ ] Every A-roll segment has an explicit `script`.
- [ ] Every B-roll segment has an explicit `tool` and a one-line "why this tool".
- [ ] Cost estimate is shown.
- [ ] The CTA is the last spoken beat (not buried mid-video).
- [ ] A recommended length is stated with rationale.

If any check fails, fix before presenting.
