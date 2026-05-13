---
name: supper-meeting-recorder
version: 0.1.1
description: "Live meeting recording for SA work. Uses Lark Calendar to identify the current meeting, starts Syncore note-taker recording, supports mid-meeting Q&A/progress summaries, and saves the final AI summary to the knowledge base. Trigger phrases: '开始录会', '开始会议录制', 'record this meeting', 'start meeting notes'."
metadata:
  requires:
    bins: ["lark-cli", "syncore"]
---

# supper-meeting-recorder — Live Meeting Recording

Use this skill when the user wants to start, monitor, summarize, or end a live meeting recording.

This is different from `supper-meeting-summary`:

| Skill | When | Source |
|---|---|---|
| `supper-meeting-recorder` | During a live meeting | Syncore mic + system audio recording |
| `supper-meeting-summary` | After meetings already ended | Lark VC + Lark Minutes history |

## Trigger Scenarios

- "开始录会"
- "开始会议录制"
- "录一下这个会"
- "start meeting recording"
- "record this meeting"
- "start meeting notes"
- "end meeting"
- "summarize so far"
- "刚才说了什么"

## Dependencies

- `lark-cli` calendar access (`calendar:calendar.event:read`)
- Syncore installed and signed in
- Syncore note-taker tools available:
  - `note_taker__start_session`
  - `note_taker__check_progress`
  - `note_taker__get_session`
  - `note_taker__end_session`
  - `note_taker__finalize_meeting`
  - `note_taker__update_speaker_name`
- `supper-sa-wiki` skill for Lark Wiki writes
- Local wiki standard from `core/local-wiki-ux.md`

Do not use Google Calendar. Current-meeting lookup must use Lark Calendar via `lark-cli`.

---

## Flow A — Start Recording

### Step 1 — If the User Already Gave a Title

If the trigger includes a clear title, skip calendar lookup.

Examples:
- "开始录会，标题叫 Acme POC sync"
- "record this meeting as Seedance weekly"

Use that title directly and ask only for missing participants if needed.

### Step 2 — Query Lark Calendar for the Current Meeting

If no explicit title was provided, use Lark Calendar as a context hint.

Compute a tight current-time window:

```bash
NOW=$(date +"%Y-%m-%dT%H:%M:%S+08:00")
START=$(date -v-10M +"%Y-%m-%dT%H:%M:%S+08:00")  # macOS
END=$(date -v+10M +"%Y-%m-%dT%H:%M:%S+08:00")

lark-cli calendar +agenda \
  --start "$START" \
  --end "$END" \
  --format json \
  --as user
```

Linux equivalent:

```bash
START=$(date -d "10 minutes ago" +"%Y-%m-%dT%H:%M:%S+08:00")
END=$(date -d "10 minutes" +"%Y-%m-%dT%H:%M:%S+08:00")
```

Candidate handling:

| Result | Agent behavior |
|---|---|
| 0 candidates | Ask: "What should I call this meeting, and who's joining?" |
| 1 candidate | Propose title + attendees and wait for explicit confirmation |
| 2+ candidates | Show a numbered picker and wait for the user to choose |

Important:
- Treat Lark Calendar as a hint, not the source of truth.
- Never silently start recording with a calendar title without confirmation.
- If calendar lookup fails, silently ask: "What should I call this meeting, and who's joining?"
- Do not mention "calendar lookup failed" or internal fallback details.

### Step 3 — Start Syncore Recording

After the title is confirmed, call:

```text
note_taker__start_session(
  title=<confirmed_title>,
  participants=<participants_or_empty_array>,
  language=<chat_or_meeting_language>,
  wiki="work",
  silence_timeout_secs=240
)
```

Language:
- Use `zh` when the user is speaking Chinese or the meeting is likely Chinese.
- Use `en` for English meetings.
- If uncertain, use `zh` for SA China/BytePlus workflows unless the title/participants suggest English.

After `start_session`:
1. Echo the returned `rendered_card` verbatim.
2. If the runtime supports scheduled/background calls, set up `check_progress` roughly every 2 minutes.
3. If scheduling is not available, do not fake it. The user can ask "summarize so far".

---

## Flow B — During the Meeting

### Progress Updates

When the user asks for a progress update, call:

```text
note_taker__check_progress(session_id="latest")
```

Follow the note-taker tool's required progress-card format.

If the response says the recording is no longer active, do not claim it is still recording. Offer to finalize the meeting from the partial transcript.

### Mid-meeting Q&A

When the user asks a question during recording:

1. Call `note_taker__get_session(session_id="latest", tail_minutes=5)` for recent context.
2. Use both:
   - the transcript
   - this chat history with the user
3. Answer with timestamps when quoting what was said.

Do not stop or finalize the session unless the user explicitly asks to end it.

### Speaker Names

If the transcript or user clarifies speaker identity, persist it:

```text
note_taker__update_speaker_name(session_id="latest", speaker=<N>, name="<display_name>")
```

Use real names in summaries whenever confidence is high.

---

## Flow C — End Recording and Save the Summary

Trigger phrases:
- "结束会议"
- "结束录会"
- "end meeting"
- "stop recording"
- "整理会议笔记"

This is a strict sequence. Do not split it across multiple turns.

### Step 1 — Stop Recording

Call:

```text
note_taker__end_session(session_id="latest")
```

The response contains the transcript, meeting language, participants, and summary protocol.

### Step 2 — Compose AI Summary

Use the transcript to produce:

- `summary`: substantive meeting summary in the meeting language
- `action_items`: array of owner-tagged tasks
- `follow_ups`: array of next-step items, parked decisions, or future checks

Rules:
- Keep the summary faithful to the transcript.
- Use real names if known; avoid `Speaker N` when participants make identities clear.
- Empty arrays are allowed; never pass `null`.

### Step 3 — Finalize Syncore Meeting

Immediately call:

```text
note_taker__finalize_meeting(
  session_id=<session_id>,
  summary=<summary>,
  action_items=<action_items>,
  follow_ups=<follow_ups>
)
```

Echo `rendered_card` verbatim.

### Step 4 — Save to the SA Knowledge Base

After the Syncore meeting is finalized, save the final AI summary and action items to the SA knowledge base.

Use the existing write path; do not duplicate write logic here:

1. Read `supper-sa-wiki` SKILL.md write workflow.
2. Submit a `CREATE` proposal for the meeting note if the meeting is new.
3. Submit an `APPEND` proposal to the customer `TIMELINE` if a customer can be identified.
4. Submit feedback / issue / risk pages only when the summary contains concrete reusable knowledge.

User-facing language:
- Do not say "dual write".
- Say "I've saved the meeting notes to the knowledge base."

### Step 5 — Save to Local Wiki When Available

Follow `core/local-wiki-ux.md`:

1. Resolve local wiki path from env, memory, or common paths.
2. If missing, ask once whether to create one using `supper-local-wiki-init`.
3. If available, save:
   - raw transcript pointer / copied transcript under `raw/`
   - source page under `wiki/sources/`
   - customer interaction update under `wiki/entities/customers/` when identifiable
   - log entry in `wiki/log.md`

Do this quietly after the main finalization card. If local wiki is not configured and the user declines setup, continue without local persistence.

---

## Output Behavior

For start/end operations, Syncore returns rendered cards. Echo them verbatim.

For additional save status, keep it short:

```text
Saved to the SA knowledge base. Local wiki updated when available.
```

Do not expose implementation terms such as:
- "double write"
- "write_queue internals"
- "Bitable constants"
- "Syncore wiki snapshot pipeline"

---

## Failure Handling

| Failure | Response |
|---|---|
| Syncore not installed | Ask the user to run `curl -fsSL https://syncorelabs.ai/install.sh \| sh`, then `syncore login` |
| Syncore not signed in | Ask the user to run `syncore login` |
| Microphone / Screen Recording missing | Ask the user to run `syncore doctor` and grant the listed permissions |
| Lark Calendar unavailable | Ask for title and participants manually; still allow recording |
| `supper-sa-wiki` write fails | Keep the Syncore finalized note and tell the user knowledge-base save needs retry |
| Local wiki missing | Ask once whether to create one |

