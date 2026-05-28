---
name: polym-explainer-video
description: Creates a polished explainer video from docs, URLs, PDFs, screenshots, or text. Triggers on requests for product/feature announcement reels, short-form demos, or repo videos. Common phrases: "make an explainer video", "produce a Shorts video", "turn this repo into a video".
---

# polym-explainer-video — Product explainer video pipeline

Upstream authorship preserved from upstream repository:
- Bo <bojsun@Bos-Mac-mini.local>
- bojsun <bojie.sun@bytedance.com>

Turns product inputs into a polished explainer video at the user-chosen aspect ratio (1:1 / 9:16 / 16:9):
- **A-roll** — an AI digital-human talking-head, generated entirely with the **Seedance 2.0** API (BytePlus ModelArk). Skipped in `pure-broll-product-demo` mode.
- **B-roll** — animated typographic / data / device-UI scenes rendered locally with **HyperFrames**.
- **Music** — AI background music from the **Volcengine** music API.

The pipeline is gated: the user must approve the storyboard before any paid generation runs.

## Language rule (read first, applies to every interaction)

**Mirror the user's language for every user-facing prompt, question, summary, and option list.** If the user is conversing in Chinese, the preflight questions, storyboard summary, approval-gate options, and any clarifying questions must all be in Chinese. Same for English, Spanish, etc. The skill's own internal reference docs stay in English (they're for the model, not the user) — but anything the user reads must match their language.

When in doubt, look at the last user message and mirror its primary language. If they mix languages, pick the dominant one.

---

## STEP 0 — Onboarding check (run this FIRST, on every invocation)

Before doing anything else, check whether the user has onboarded:

```bash
cat ~/.explainer-video/config.json 2>/dev/null
```

- **File missing or empty** → run the **§ Onboarding** flow below, then continue to the per-task workflow.
- **File present** → load it and go straight to **§ Per-task workflow**.

`config.json` schema:
```json
{
  "modelark_api_key": "<ModelArk API key>",
  "iam_ak": "<BytePlus IAM access key>",
  "iam_sk": "<BytePlus IAM secret key>",
  "portrait_image": "/abs/path/to/personal-photo.jpg",
  "reference_video": "/abs/path/to/portrait-video-with-audio.mov",
  "output_folder": "/abs/path/to/save/folder",
  "music_enabled": true,
  "volc_music_ak": "<Volcengine access key — only present if music_enabled is true>",
  "volc_music_sk": "<Volcengine secret key — only present if music_enabled is true>",
  "onboarded_at": "YYYY-MM-DD"
}
```

When `music_enabled` is `false`, `volc_music_ak` / `volc_music_sk` are omitted and
the per-task workflow skips music generation entirely.

---

## Onboarding (first run only — all in English)

When `config.json` is missing, walk the user through this once. Keep it friendly and concise.

**1. Explain what the skill does** — show the user:

> "This skill turns product information into a polished explainer video (square, vertical, or landscape — your choice per task).
> Feed it Lark/Feishu docs (requires the Lark CLI to be installed and authorized),
> GitHub repos, screenshots, PDFs, or a plain description — and it generates, in one
> flow, a complete video. Three modes:
>   · **pure-broll-product-demo** (default for repo/product demos) — no on-camera presenter; polished motion + UI
>   · **aroll-broll-hybrid** — adds an AI digital-human talking-head (Seedance 2.0)
>   · **aroll-only** — minimal, just the avatar
> With optional background music. Let's get you set up — it takes a minute."

**2. Choose how to provide credentials.** Ask:

> "You can onboard two ways:
>  **(a) Credential file** — paste the path to a filled-in copy of `credentials.template.md`.
>       Handy if a teammate already sent you a completed one.
>  **(b) Step-by-step** — I'll ask for each item in turn.
> Which do you prefer? (a / b)"

- A blank template lives at `<skill>/credentials.template.md`. Tell the user they can fill
  it and send it to teammates so they can onboard in one step.
- **If (a):** read the file, parse the `key: value` lines, and validate that every required
  field is present and non-placeholder. Write `config.json` from it. If anything is missing
  or still a placeholder, fall back to asking **only** for the missing items step-by-step.
- **If (b):** continue with steps 3–7 below.

**3. Collect the ModelArk API key.**
Ask: *"Paste your BytePlus ModelArk API key (used to generate Seedance 2.0 video and Seedream images)."*

**4. Collect the BytePlus IAM AK / SK.**
Ask: *"Paste your BytePlus IAM access key (AK) and secret key (SK). These are used to operate the ModelArk asset library and TOS object storage."*

**5. Collect the personal portrait assets.**
Ask: *"Provide two files for the digital-human A-roll:
  (a) a clear front-facing personal photo, and
  (b) a short portrait video of yourself talking, WITH audio.
The photo drives the avatar's appearance; the video drives the voice and facial motion."*
Record the absolute paths.

**6. Ask for the preferred output folder.**
Ask: *"Where should finished videos be saved? (press Enter for the default `~/Downloads`)"*

**7. Ask about automatic AI music.**
Ask: *"Do you want automatic AI background music for your videos? (yes / no)"*
- **If yes** → set `music_enabled: true` and ask:
  *"Paste your Volcengine access key (AK) and secret key (SK) — used by the Volcengine
  music model to generate background tracks."* Record `volc_music_ak` / `volc_music_sk`.
- **If no** → set `music_enabled: false` and skip the Volcengine keys. The per-task
  workflow will produce videos without a music bed.

**8. Write the config** to `~/.explainer-video/config.json` (create the dir, `chmod 600` the file). Confirm: *"Setup complete — you're ready to make videos."*

> Per-task steps (portrait restyle, storyboard review) are NOT part of onboarding — they run on every task. See § Per-task workflow.

---

## Per-task workflow

Run these phases in order for every video. Never skip the Phase 3 approval gate.

### Phase 1 — Intake + Preflight

1. List the user's inputs and categorize: `text_docs`, `github_url`, `lark_doc`, `screenshots`, `pdfs`, `chat_description`.
2. Extract content:
   - **Lark/Feishu docs** — fetch with `lark-cli docs +fetch --api-version v2 --doc <token> --as user`. (Requires lark-cli installed + authorized.)
   - **GitHub URL** — `web_fetch` the repo for README, stars, recent commits.
   - **Screenshots / PDFs** — read with vision / the pdf skill.
   - **Chat description** — treat as the user's stated intent.
3. Produce `product-brief.md` (what it is, core differentiators, audience, visual assets, stated angle). Show it and confirm.

#### Preflight (PRs #1 + #12) — ask BEFORE drafting any storyboard

These two questions shape every downstream decision (layout, aspect ratio, motion, file size). Get them out of the way before storyboard work.

**Q1 — Production mode** (PR #1)

> "Three modes — which fits this video?
>   (a) **pure-broll-product-demo** — no on-camera presenter; polished motion + UI shots (OpenAI/Apple style). Default for repo / product / feature demos.
>   (b) **aroll-broll-hybrid** — adds a Seedance 2.0 AI digital-human talking-head intro + outro. For personal-brand / creator videos.
>   (c) **aroll-only** — just the avatar, minimal B-roll. Rare; choose only if the content IS the speaker."

Auto-suggest:
- GitHub repo + screenshots, no "I want to be on camera" signal → recommend `(a) pure-broll`
- User explicitly mentions themselves, has portrait/reference video onboarded → recommend `(b) hybrid`

Write `mode: "<choice>"` to storyboard.json.

**Q2 — Visual identity** (PR #12)

> "Where should I source the visual style?
>   (a) **Your own brand** — paste a design.md path, or describe colors/fonts inline
>   (b) **Built-in preset** (copyright-safe, inspired-by treatment):
>       · `openai-clean`      — white bg, geometric bold sans, lavender liquid, minimal
>       · `anthropic-warm`    — warm earth tones, sparkle accents, serif/sans pairing
>       · `linear-minimal`    — dark mode, neon accent, technical
>       · `apple-keynote`     — dark backdrop, hero typography, soft depth
>       · `brand-bold`        — high-contrast, oversized type, color-block"

See `references/style-presets.md` for full preset docs. Default suggestion based on product type:
- AI/coding agent + repo → `openai-clean`
- Quiet B2B → `anthropic-warm`
- Developer infrastructure → `linear-minimal`
- Single-hero-product launch → `apple-keynote`
- Loud launch / event → `brand-bold`

Write `style_preset: "<choice>"` to storyboard.json. If user supplies their own design.md, copy it to project root and write `style_preset: "custom"`.

**Q3 — Distribution channel** (PR #12)

> "Where will this video live?
>   (a) **X / LinkedIn / IG feed**       → 1:1 square (1440×1440)
>   (b) **TikTok / Reels / YT Shorts**   → 9:16 portrait (1080×1920)
>   (c) **YouTube / website hero**       → 16:9 landscape (1920×1080)
>   (d) **Multi-channel**                → primary 1:1 + auto-generate 9:16 + 16:9 variants (charged: ~3× render time)"

See `references/channel-aspect-ratios.md` for the full table + safe-zone info. Write `channel: "<choice>"` and `aspect_ratio: "<ratio>"` to storyboard.json.

The channel also implies a sweet-spot duration. Phase 3 will compare your storyboard's length to that range and flag if off.

After all 3 preflight answers are recorded, proceed to Phase 2.

### Phase 2 — Optional portrait restyle with Seedream 4.5

> **Skip Phase 2 entirely** if `mode` from Phase 1 is `pure-broll-product-demo` — no avatar means no portrait. Jump to Phase 3.

At the start of **every new task** (in `aroll-broll-hybrid` or `aroll-only` modes), ask:

> *"Want to restyle your portrait for this video — a new outfit, environment, or lighting — with Seedream 4.5? (yes / no)"*

If **yes**:
1. Ask the user for a styling prompt (outfit, setting, mood).
2. Generate **4 variations** with Seedream 4.5 (see `references/seedream-api.md`).
3. Show all 4 and let the user **review**: pick one, regenerate with a revised prompt, or skip.
4. The chosen image becomes the portrait for this task's A-roll. If the user skips, use `config.portrait_image`.

If **no** → use `config.portrait_image` directly.

### Phase 3 — Storyboard + shot design (APPROVAL GATE)

Before any paid generation, design and present:

**0a. Surface design context from Phase 1 preflight** (PR #12):

   > "This storyboard targets **{channel}** at **{aspect_ratio}** using the **{style_preset}** visual identity, in **{mode}** mode. The {channel} sweet-spot duration is {lo}–{hi}s. Confirm or change before I draft the storyboard."

   If the user wants to change a preflight answer, do it NOW (not after storyboard is drafted) — the storyboard is shaped by these answers.

**0b. Establish the narrative arc BEFORE drafting any UI scenes** (read `references/narrative-arc.md` — this is the most important reference in the skill).

   Drafting order is **non-negotiable** — do these IN ORDER before writing any segment:

   1. **Cast** — name the protagonist (e.g., "Erica, eng lead at her startup"). NOT "the user" or "the developer". Add 1-3 named supporting characters.
   2. **Canon** — list 3-5 specific entities preserved across every frame: the meeting name, the other party (with email if relevant), the central quoted commitment, the key document, background context. Proper nouns, not categories.
   3. **Echo** — pick ONE canon entity that will recur across 2+ frames in the same typography. This is the visual rhyme that makes the story feel intentional. (Reference Syncore: the quoted commitment appears in frames 3, 6, and 7 — same italic serif each time.)
   4. **Narrative answers** — protagonist / problem / moment_of_magic / memorable_line / cta.
   5. **Frame-name keywords** — 1 short UPPERCASE word per planned segment (SUMMON / DETECT / KEPT / etc).
   6. **Narration cue per frame** — exact spoken line + numbered cue_id (`"03 · DETECT"`) OR explicit `silent: true` with reason. No frame without one.
   7. **Click chain** (UI products only) — list the cursor clicks that trigger scene transitions, with timestamps.
   8. **arc_map** — map segments to the 5 beats (+ optional breather). Magic must be the longest combined.
   9. **Now draft segments.**

   The auditor (`audit_storyboard.py`) will block render if any of: `narrative` has REPLACE: placeholders, canon has < 3 entries, cast.protagonist is abstract, arc_map missing a beat, magic shorter than reveal × 0.7, or 3+ device-mockups without arc_map.

   **If you can't fill steps 1-7 confidently, STOP and ask the user clarifying questions BEFORE drafting segments.** Use AskUserQuestion in their language. The screen catalogue mistake (UI screens with no narrative thread) is the #1 reason finished videos don't communicate.

   **The storyboard.md you produce for the approval gate MUST include these 4 sections** (storyline-as-handoff-document pattern):
   - Timeline table (frame # · time · frame_name · what happens · narration cue)
   - The canon (preserved entities)
   - What drives the narrative forward (click chain or beat triggers)
   - What's locked (target duration, aspect, style preset, planned output path)

1. **Recommended length** — pick from the content profile and state the reasoning:

   | Content profile | Recommended length | content_profile key |
   |---|---|---|
   | Single clear message, broad audience | **25–35s** | `single-message` |
   | 2–4 features, moderate explanation | **40–55s** | `few-features` |
   | Many distinct workflows / skills to cover | **65–90s** | `many-features` |

   > **Bias toward compression** (PR #11). Earlier defaults (20-30 / 45-60 / 75-110) consistently produced videos with dead air at the end. A 45s narrative will land more cleanly at 32s — same content, denser pacing. If a target seems too long for the content, shorten before approval.

2. **Storyboard** — a segment-by-segment beat sheet. For each segment specify: time range, type (`A-roll` / `B-roll`), on-screen content, and for A-roll the spoken script.

3. **A-roll / B-roll routing:**
   - **A-roll (Seedance 2.0)** — talking-head segments. Typically a hook/intro and a closing CTA. Keep each 5–10s.
   - **B-roll (HyperFrames)** — everything else: typographic scenes, skill/feature demos, data callouts, kinetic-typography hooks, brand reveal. Rendered locally, no per-clip cost.

4. **Music plan** — only if `config.music_enabled` is `true`. From the task context
   (the product brief, the storyboard mood, the pacing) **draft a suggested music
   generation prompt** and present it as the default. Example:
   *"Suggested music prompt: 'upbeat modern tech-product launch, driving synth, optimistic,
   instrumental, builds to an energetic finish'. Use this, or give me your own?"*
   The user can accept the suggestion or replace it. If `music_enabled` is `false`, state
   that the video will have no music bed and skip this item.

5. **Cost estimate** — Seedance tokens (A-roll), Volcengine music (if enabled), HyperFrames $0. Show it.

6. **Run the unified verifier** (PRs #7 + #11 + Wave 5) BEFORE presenting:

   ```bash
   python3 <skill>/scripts/verify.py storyboard.json --mode pre --auto-fix
   ```

   This runs ALL pre-render checks: `audit_storyboard` (dead air / duration / density / mode / overflow estimate), `check_overlap` (z-layer collisions), `check_assets` (asset existence + embedded-video keyframes), and hyperframes `lint+validate+inspect`. With `--auto-fix`, it loops until severe issues are mechanically resolved or no further fixes are possible.

   **Resolve every severe finding** before approval. Warnings (dead air, duplicates) need human judgment — surface them to the user. Auto-fixable issues (camera overflow, track collisions, sparse keyframes) get repaired automatically; verify.py's report will say what it changed.

7. **Approval gate — present everything, then offer EXACTLY 3 options via AskUserQuestion (in the user's language):**

   - **Approve** → proceed to Phase 4. The wording in the user's language should clearly mean "approved, render it"
   - **Specific changes** → user types what to change; the model revises the storyboard, re-runs verify, and re-presents. **Loop until the user picks approve or stop.**
   - **Stop generation** → abort the task cleanly; nothing renders, no money spent

   Implementation pattern:
   ```
   AskUserQuestion (question and options in user's language) with these 3 choices:
     1. Approve / 通过 / Aprobar
     2. Suggest changes / 输入具体修改建议 / Sugerir cambios
     3. Stop / 停止生成 / Detener
   ```

   **Important**: do NOT proceed on "looks good", "👍", or any phrasing that isn't one of the three explicit options. Render is the expensive step — make the user click "approve" explicitly.

   On "specific changes": ask what to change, revise the storyboard, re-run `verify.py --mode pre --auto-fix`, then re-present the 3-option gate. No render-then-fix.

   On "stop": acknowledge, do nothing, leave the storyboard files on disk for inspection.

### Phase 4 — Production

Runs only after Phase 3 approval.

> **Before writing any GSAP code**: read [`references/motion-house-style.md`](references/motion-house-style.md) — non-negotiable easings, frame rate, duration windows, exit-animation rules. Skipping this consistently produces "feels cheap" motion that requires a second render pass to fix. Render is the expensive step.

1. **Workspace** — `mkdir -p` a project dir; `cp -r <skill>/assets/* .`; `cp -r <skill>/templates/* .` (if using any reusable templates like agent-chip-row.html); `npm install` (downloads HyperFrames).
2. **A-roll** — generate every talking-head segment with Seedance 2.0 (only if mode is `aroll-broll-hybrid` or `aroll-only`). See § A-roll generation.
3. **B-roll** — build the HyperFrames composition (`index.html`); render at **60fps `--quality high`** via `scripts/compose_and_render.py` (which now passes these flags by default — PR #2). See `references/production-techniques.md`.
4. **Music** — only if `config.music_enabled` is `true`: generate BGM with the Volcengine API, using the music prompt approved in Phase 3. See `references/volcengine-music-api.md`. If `music_enabled` is `false`, skip this step.

4b. **Beat-align (optional, PR #10)** — if `references/storyboard-format.md` lists segments with `snap_to_beat: true`, run:
   ```bash
   python3 <skill>/scripts/beat_align.py storyboard.json assets/music_bed.m4a
   ```
   This snaps transition/beat times to the nearest detected music onset (±150ms). Re-renders the composition with the aligned storyboard before step 5. Falls back silently if `librosa` isn't installed.

5. **Assemble** — slice the HyperFrames render, concat with the A-roll segments. If music was generated, mix the music bed (sidechain-duck the music under any A-roll voice). See `references/production-techniques.md`.

6. **Meta-output beat (PR #8, optional)** — if the storyboard includes a `meta-output` segment with `strategy: "recursive-video"`, this is the place to do the **two-pass** render: skip the meta beat in pass 1, re-encode with dense keyframes, embed in pass 2. See `references/meta-output-beat.md` for the full pipeline. The default `strategy: "synthetic"` doesn't require two passes.

7. **Post-render verifier** (Wave 5) — `compose_and_render.py` automatically runs:

   ```bash
   python3 <skill>/scripts/verify.py storyboard.json --mode post \\
     --rendered dist/main.mp4 --auto-fix
   ```

   Checks: pixel-based overflow detection (`validate_overflow`), render-spec match (resolution/fps/duration vs declared), audio levels in mode-target range, no clipping. Auto-fix can re-mux the audio gain in place; overflow/spec issues require user attention (re-render with adjusted parameters).

   If `--no-auto-fix` is passed to compose_and_render.py, the verifier reports but doesn't repair. Use `--force` to render even when pre-render verification flags severe issues.

### Phase 5 — Deliver

Save the final MP4 to `config.output_folder` (default `~/Downloads`). Report duration, size, and path. Offer to upload to Lark (see `references/lark-upload-guide.md`) — never upload without explicit confirmation.

---

## A-roll generation — Seedance 2.0 only

A-roll is generated entirely with the Seedance 2.0 API. Full API details, endpoints, the asset-library workflow, and Python helpers are in **`references/seedance-api.md`** — read it before generating. Two modes:

### Mode A — image + text (native 9:16, generated voice)
Portrait image + a text prompt containing the spoken line → a talking-head that speaks the line with Seedance's own generated voice. Honors `aspect_ratio: "9:16"` natively. Best when you want exact scripted wording and don't have a reference video.

### Mode B — r2v (reference-to-video)
Portrait image (appearance) + a reference video (voice character + facial-muscle motion) → a talking-head. **The output follows the reference video's aspect ratio**, so the reference video must itself be 9:16 to get a 9:16 result. Best when you want the user's real voice and natural facial performance.

**Critical r2v constraints (learned the hard way — do not skip):**
- The reference video must be **9:16** for 9:16 output. Centre-crop a landscape source.
- Reference video duration must be **≤ 15.2 s**.
- Asset-library video assets must be **409,600–2,086,876 pixels** (e.g. 720×1280 or 1080×1920).
- Real-person photos/videos passed as raw URLs are **blocked by content moderation**. You MUST upload them to the ModelArk **asset library**, wait for `Status: Active`, then reference them with the **`asset://<AssetId>`** scheme — approved assets bypass re-moderation. This is the only working path for real-person A-roll.

When the storyboard's A-roll segments need specific spoken lines, **put the script in the text prompt** even in r2v mode.

---

## References (load on demand)

| File | Content |
|---|---|
| `references/seedance-api.md` | Seedance 2.0 video API — endpoints, asset library (SigV4), `asset://`, r2v + image+text modes |
| `references/seedream-api.md` | Seedream 4.5 image API — the Phase 2 portrait restyle (4-variation generate) |
| `references/volcengine-music-api.md` | Volcengine BGM API — GenBGM/QuerySong, similarity-retry, mixing |
| `references/storyboard-format.md` | Storyboard JSON/markdown spec |
| `references/production-techniques.md` | HyperFrames composition, slicing, concat, sidechain ducking, kinetic typography |
| `references/hook-patterns.md` | Hook templates for short-form video |
| `references/broll-routing.md` | B-roll scene-type decision guide |
| `references/cost-rates.md` | Current Seedance / Volcengine rates |
| `references/lark-upload-guide.md` | lark-cli upload commands |
| `references/reference-video-analysis.md` | Extracting style from a reference clip |
| `references/motion-house-style.md` | **PR #2** — non-negotiable easing/fps/timing rules; read before authoring any GSAP |
| `references/agent-list.md` | **PR #9** — canonical brand info for known AI coding agents (Claude Code, Codex, OpenClaw, Hermes, …) |
| `references/narrative-arc.md` | **CRITICAL — read before drafting any storyboard.** Codifies the 5-beat narrative arc (hook → tension → reveal → magic → promise). Prevents the "screen catalogue" failure mode where the video shows UI but doesn't tell a story. |
| `references/hyperframes-catalog.md` | **PR #4** — curated subset of the HyperFrames registry (~15 high-value blocks) with when-to-use |
| `references/style-presets.md` | **PR #12** — 5 built-in design presets (openai-clean, anthropic-warm, linear-minimal, apple-keynote, brand-bold) + when-to-use |
| `references/channel-aspect-ratios.md` | **PR #12** — distribution channel × aspect-ratio × duration matrix with safe-zone info |
| `references/caption-components.md` | **PR #3** — curated 4 caption components + selection guide per preset |
| `references/screen-script-format.md` | **PR #5** — how to script the in-device screen HTML (live-UI vs raw-screenshots) |
| `references/meta-output-beat.md` | **PR #8** — multi-shot result preview (synthetic vs recursive-video strategies) |

## Scripts

`scripts/` holds helpers. They use stdin/stdout/JSON and never write outside the working directory.

| Script | Purpose |
|---|---|
| `preflight.py` | Pre-flight environment checks |
| `parse_inputs.py` | Categorize user inputs (text/url/pdf/screenshot) |
| `estimate_cost.py` | Pre-Phase-3 cost estimate (Seedance tokens + Volcengine music) |
| `analyze_reference_video.py` | Extract style data from a reference clip |
| `compose_and_render.py` | Phase 4 orchestrator — assembles index.html, renders at **60fps high quality** (PR #2) |
| `audit_storyboard.py` | **PR #7 + #11** — dead-air detector + duration target + pacing audit. Run in Phase 3 BEFORE the approval gate. |
| `fetch_registry.py` | **PR #4** — fetches + caches HyperFrames registry (24h TTL). Use for discovering blocks. |
| `validate_overflow.py` | **PR #6** — post-render frame sampler; flags content within Npx of canvas edge (catches camera-zoom overflow that lint misses) |
| `synthesize_screen_ui.py` | **PR #5** — generates the in-device screen HTML (LLM mode) OR cross-fades raw screenshots (fallback mode) |
| `beat_align.py` | **PR #10** — snap segment transitions to music onsets (±150ms). Requires librosa. |
| `check_overlap.py` | **Wave 5** — detects same-track collisions + unintended visible overlap between segments |
| `check_assets.py` | **Wave 5** — verifies referenced assets exist + embedded videos have dense-enough keyframes |
| `check_render_spec.py` | **Wave 5** — post-render: confirms rendered MP4 matches storyboard's declared resolution/fps/duration |
| `check_audio_levels.py` | **Wave 5** — post-render: checks audio mean RMS in mode-target range + no clipping |
| `verify.py` | **Wave 5** — unified validator orchestrator with auto-fix loop. Runs all validators, applies mechanical repairs (cap scales, re-encode video keyframes, re-mux audio gain, deconflict tracks), re-verifies up to N iterations. Wired into compose_and_render.py pre + post render. |
| `upload_to_lark.py` | Optional Phase 5 upload to Lark |

## Templates

`templates/` holds reusable HTML snippets / recipe scaffolds:

| Template | Purpose |
|---|---|
| `agent-chip-row.html` | **PR #9** — opening pattern with a row of agent icons + labels. Edit the markup per task. |
| `openai-product-demo.json` | **PR #5** — canonical storyboard recipe for `mode: pure-broll-product-demo`. Drop in and customize. |

## Assets

| Asset | Purpose |
|---|---|
| `hyperframes-template.html` | Templated index.html scaffold with placeholders for width/height/duration/bg/font (PR #1 + #12) |
| `style-presets/<name>/design.md` | 5 built-in design presets (PR #12) — see `references/style-presets.md` |
| `macos-window-chrome.html` | **PR #5** — reusable macOS window chrome (titlebar + traffic lights + optional QT transport bar) |

---

## Security and safety

- All credentials (ModelArk key, BytePlus IAM AK/SK, and — if music is enabled — Volcengine music AK/SK) come from `~/.explainer-video/config.json` (mode 600) — never hardcode, never print in full.
- A blank `credentials.template.md` is shipped for teammates to fill in and share; a filled-in copy is sensitive — treat it like the config file and never commit or upload it.
- All paid operations require the Phase 3 approval gate. If asked to skip it, push back.
- Never upload or share a finished video without explicit user confirmation.
- Respect content moderation — never attempt to bypass real-person or copyright checks.
