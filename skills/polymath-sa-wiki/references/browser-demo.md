# Browser Demo — Optional Read-Path Renderer

> Invoked from [`../SKILL.md`](../SKILL.md) §4 "Demo Offer". This file is a **reference**, not a separate skill — there is no new trigger, no schema change, no new entity type. Wiki content is used as-is.

Goal: when a wiki page describes a browser-operable procedure (e.g. "how to create an AK/SK", "how to open BABI", "how to apply for a quota"), let the agent **demo it live in the SA's own Chrome** instead of (or in addition to) returning markdown.

---

## 1. When to Offer Demo (heuristic scoring)

Score the fetched doc body. Sum the signals:

| Signal | Weight |
|---|---|
| Contains one or more `https?://` URLs pointing to a console / portal / platform | +2 |
| Contains action verbs (`点击` / `进入` / `选择` / `打开` / `复制` / `click` / `select` / `open` / `paste`) ≥ 3 times | +2 |
| Contains a numbered list or `Step N` / `第 N 步` markers | +2 |
| Contains UI location references (`右上角` / `左侧导航` / `top right` / `sidebar`) | +1 |
| Mentions specific button or menu names by quoted string | +1 |

**Threshold:**
- **Score ≥ 4** → recommend "browser demo" as the first option in the offer line
- **Score 1–3** → still offer demo, but list "read-only" first
- **Score 0** → do not offer demo; just answer the question

**User overrides:** if score is low but user explicitly says "演示" / "demo it", honour them — say "I'll parse what I can; the page isn't very operational so the demo may be partial" and proceed.

---

## 2. MCP Availability Check (do this BEFORE starting demo)

Verify the Claude in Chrome MCP toolset is available:
- Tools should appear with prefix `mcp__Claude_in_Chrome__*` (e.g. `navigate`, `find`, `computer`, `javascript_tool`, `gif_creator`, `tabs_*`).
- If unavailable (user hasn't installed Claude in Chrome): gracefully fall back:
  > "I'd love to demo this but Claude in Chrome MCP isn't connected. Want me to walk you through it as text instead?"

Do **not** use `mcp__Claude_Preview__*` — that's headless and the user can't watch.

---

## 3. Demo Execution Flow

### 3.1 Parse the doc into a step list (in memory)
- Don't write parsed steps anywhere; they live only in this turn.
- Extract per step: target URL (or "stay on current page"), target UI element (by visible text / location hint), narration (1–2 sentences for the SA), optional callout (warnings).
- Show the parsed step list to the SA first as a 1-line preview ("I parsed N steps, ETA ~X min — start?") so they can correct before you start clicking.

### 3.2 Tool mapping

| Need | Tool |
|---|---|
| Open / change page | `mcp__Claude_in_Chrome__navigate` |
| Find an element (with text-based fallback) | `mcp__Claude_in_Chrome__find` + `mcp__Claude_in_Chrome__get_page_text` |
| Click / type / hover | `mcp__Claude_in_Chrome__computer` or `mcp__Claude_in_Chrome__form_input` |
| Inject visual aids (red box, tooltip) | `mcp__Claude_in_Chrome__javascript_tool` |
| Record the whole demo as GIF | `mcp__Claude_in_Chrome__gif_creator` |
| Tab management | `mcp__Claude_in_Chrome__tabs_*` |
| Verify state before proceeding | `mcp__Claude_in_Chrome__read_page` |

### 3.3 Rhythm rules (CRITICAL — most common failure)

- **Never run all steps in one shot.** Pause after each step. Without pauses, the SA can't follow what the cursor just did.
- Per-step pattern:
  1. `navigate` to URL (if step changes page) — wait for load
  2. `find` target element by visible text
  3. `javascript_tool` → inject highlight on target (see §3.4)
  4. Narrate to the SA in chat: 1–2 sentences explaining what's highlighted and what will happen
  5. Wait for SA to type `next` / `下一步` / `继续` / equivalent before doing the click
  6. `computer` / `form_input` → perform the action
- For pages with async loading, use `read_page` to verify expected text appeared before moving on.

### 3.4 Visual aids via `javascript_tool`

Inject a small JS snippet that:
- Adds a 3px solid red outline around the target element (`element.style.outline = '3px solid #ff3b30'; element.style.outlineOffset = '2px';`)
- Optionally adds a floating tooltip bubble near the element containing the step's narration
- **Always remove the previous step's highlight before adding the new one** (track via a known CSS class, e.g. `.polymath-demo-highlight`)

### 3.5 GIF recording

- Start `gif_creator` at step 1.
- Stop & export at the end of the demo (after the last step or on graceful abort).
- Default save path: `~/Desktop/polymath-demo-<slug>-<YYYYMMDD-HHMM>.gif` where `<slug>` is a kebab-case form of the tutorial title.
- Before saving, ask the SA: "Screen contains anything customer-identifying? I can skip saving the GIF if you'd rather not keep it." Default to saving if they say no / don't answer.

---

## 4. Boundaries (what NOT to do)

| Risk | Rule |
|---|---|
| **Sensitive actions** (creating real AK/SK, payment, prod deletion, account changes) | Demo up to the **last click before commit** — let the SA press the final button themselves. Never auto-confirm. |
| **Selector keeps failing** (UI changed) | Try LLM visual fallback via `computer` tool's screenshot mode once. If it fails twice on the same step, **stop the demo gracefully**: "UI may have changed at step N — here's the wiki text from this step onwards" and dump the rest of the markdown. |
| **Privacy** | Before saving GIF, ask permission (see §3.5). Never upload the GIF anywhere automatically. |
| **Language mismatch** | Detect doc language (zh vs en). BytePlus console has both zh/en UI — match the active UI language when finding elements. If the doc is zh but the user's console is en, narrate in zh but find by English UI text. |
| **Skipping rhythm** | Tempting to chain `navigate → click → click` in one shot. Don't. The whole point is the SA watches. |

---

## 5. Post-Demo Feedback Loop (optional)

After the demo completes, if you noticed gaps in the wiki page during execution — for example:
- A step that needed a warning the doc didn't have ("SK only shows once! Copy it now")
- A step that needed a precondition the doc didn't mention
- A selector hint that's stale because UI changed

Offer:
> "💡 I noticed the wiki page could be improved: <specific gap>. Want me to propose a patch via write_queue?"

If yes, follow the standard write_queue flow in [`../SKILL.md`](../SKILL.md) §5 — submit an `APPEND` proposal against the same `target_doc_token`, with `source_refs` set to "browser-demo session on <date>". **Do not modify wiki schema; this is just a normal proposal.**

---

## 6. Reusability Note

This reference file intentionally lives under `polymath-sa-wiki/references/` rather than a shared skill, because:
- The demo capability has no independent trigger — it always enters via the wiki read path.
- A separate skill would create trigger ambiguity ("how to create AK" → wiki or demo?), which the user explicitly rejected.

If a **future skill** (e.g. `polymath-help` showing how to install Polymath itself) wants the same browser-demo behaviour, it should `Read` this file from its own SKILL.md rather than re-implement. Treat this file as the team's shared demo runbook — but only invoked, never triggered.

---

## 7. Quick Reference — Offer Line Templates

After parsing & scoring, append one of these to your reply:

**Score ≥ 4:**
> 📺 This page contains operational steps. Want me to walk you through it in the browser?
> (1) browser demo  (2) read-only (already given above)  (3) re-search

**Score 1–3:**
> This page has a few operational hints. I'd suggest reading the text above first; if you want, I can also try to demo it:
> (1) read-only (given above)  (2) browser demo (may be partial)  (3) re-search

**Score 0:** no offer.
