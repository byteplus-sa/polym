---
name: polym-slack-digest
description: "Generate Slack daily digests, highlight customer risks and action items, and publish summaries to Lark or local outputs."
allowed-tools: "Bash, Read, Write, Edit"
version: "1.2.0"
---

# Slack Daily Digest Skill

End-to-end Slack-to-Feishu daily intelligence pipeline. The skill handles the full lifecycle on Mira, Codex, and Claude Code:

1. **Onboarding** — guide the user to create a Slack App, install it to their workspace, and configure both Slack and Lark Bot credentials.
2. **Index Setup** — create a single Feishu doc that lists every daily digest, newest at top.
3. **Schedule** — register a recurring task at the user-specified time (default: `11:00` and `16:00` in the configured timezone).
4. **Daily Run** — pull, synthesize, write per-day doc, pin to index.
5. **Watchdog** — 20 minutes after run, verify the doc exists and contains expected sections; if not, diagnose and retry until success.
6. **Notify** — push Highlights + TODO summary to user via Lark IM bot.

---

## Platform Matrix

| Platform | Lark docs | Scheduling | Durability | Retry/catch-up |
|---|---|---|---|---|
| Mira | Built-in Lark doc skills | Mira scheduled task | Durable | Mira watchdog + retry |
| Codex | Local Lark CLI | Durable Codex routines (MCP) | Durable UI | Durable retry routine (+15 min) |
| Claude Code | Local Lark CLI | Durable scheduled tasks (MCP) | Durable UI | Durable retry routine (+15 min) |

For Codex and Claude Code, all scheduled routines are **durable host UI routines** — they persist across session restarts and are visible/manageable in the host's routine/automation UI. Local OS schedulers (launchd, cron, systemd) are not used.

For one-off E2E runs, the current host agent handles synthesis via the `HOST_AGENT_HANDOFF` file. Do not look for a `codex` or `claude` executable for this path.

## 0. Conventions

- **Working directory**: All persistent files live under `~/.slack-daily-digest/`. The skill creates this on first run.
- **Credential file**: `~/.slack-daily-digest/credentials.json` (mode 0600). Never echo credentials back to the user.
- **State files**:
  - `~/.slack-daily-digest/users_cache.json` — Slack user ID → name/title/email
  - `~/.slack-daily-digest/channel_owner_cache.json` — channel → BytePlus owner
  - `~/.slack-daily-digest/index.json` — index doc URL + folder token + schedule
  - `~/.slack-daily-digest/routine.json` — local Codex / Claude Code routine configuration
  - `~/.slack-daily-digest/routine_state.json` — local routine slot attempts and catch-up state
  - `~/.slack-daily-digest/runs/<YYYY-MM-DD>/` — per-day pull/synth artifacts

- **Output language**: All user-facing prompts, doc titles, and digest content **default to English**. The skill may switch to the user's working language only if the user explicitly asks.

---

## 1. Routing — When to Trigger Each Phase

Read `~/.slack-daily-digest/credentials.json`:
- **Missing or incomplete** → run **Phase A: Onboarding** (§2)
- **Complete but no `index.json`** → run **Phase B: Index Setup** (§3)
- **Codex / Claude Code local mode and no `local_platform.json`** → run `scripts/setup_lark_cli.py`, then continue setup when ready
- **All present, user asks "run digest now"** → run **Phase D: Daily Run** (§5)
- **All present, user asks "verify today" / triggered 20min after run** → run **Phase E: Watchdog** (§6)
- **User asks "change schedule" / "reconfigure"** → re-run the relevant phase

Platform detection is centralized in `scripts/platform.py`. Honor `SLACK_DIGEST_PLATFORM=mira|local_agent` when present; otherwise Mira-specific runtime hints select Mira, and all other environments use local-agent mode.

---

## 2. Phase A — Onboarding (Slack App + Lark Bot)

Show the user **two parallel setup tracks** in one message. Both must be completed before proceeding.

### 2.1 Slack App Setup

Display this verbatim (English):

> **Step 1 — Create your Slack App**
>
> 1. Go to https://api.slack.com/apps and click **Create New App** → **From scratch**.
> 2. Name it `Mira Slack Digest` and pick your workspace.
> 3. In **OAuth & Permissions** → **User Token Scopes**, add:
>    - `channels:history`, `channels:read`
>    - `groups:history`, `groups:read`
>    - `im:history`, `im:read`
>    - `mpim:history`, `mpim:read`
>    - `users:read`, `users:read.email`
> 4. Click **Install to Workspace** and authorize.
> 5. Copy the **User OAuth Token** (starts with `xoxp-...`) and paste it back here.
>
> ⚠️ Use the **User Token**, not the Bot Token — the digest reads channels you joined as a user.

After the user pastes the token, validate it:

```bash
curl -s -H "Authorization: Bearer $SLACK_USER_TOKEN" \
  "https://slack.com/api/auth.test" | jq '.ok, .user, .team'
```

If `ok=false`, show the error and ask them to retry.

### 2.2 Lark Bot Setup

> **Step 2 — Create your Lark Custom Bot**
>
> 1. Go to https://open.feishu.cn/app and click **Create Custom App**.
> 2. Name it `Mira Slack Digest Notifier`.
> 3. In **Permissions & Scopes**, add:
>    - `im:message` (send messages)
>    - `im:message:send_as_bot`
>    - `contact:user.base:readonly` (resolve email → open_id)
>    - `docx:document` (read/write docs)
>    - `drive:drive` (move docs to folder)
> 4. In **Version Management & Release**, publish v1.0 and wait for admin approval (or self-approve in trial workspaces).
> 5. In **Credentials & Basic Info**, copy **App ID** and **App Secret** and paste both here.

Validate by acquiring a tenant access token:

```bash
curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$LARK_APP_ID\",\"app_secret\":\"$LARK_APP_SECRET\"}" | jq '.code, .tenant_access_token'
```

`code=0` means success.

### 2.3 Persist Credentials

Use `scripts/save_credentials.py`:

```bash
python3 ~/.claude/skills/slack-daily-digest/scripts/save_credentials.py \
  --slack-token "xoxp-..." \
  --lark-app-id "cli_..." \
  --lark-app-secret "..." \
  --lark-user-email "<the user's lark email>"
```

This writes `~/.slack-daily-digest/credentials.json` with mode `0600`.

Then proceed to **Phase B**.

---

## 3. Phase B — Index Setup & Schedule

Use `scripts/platform.py` to select the setup path.

### 3.0 Local-Mode Notice

When the platform is Codex / Claude Code local mode, tell the user:

> I will create **durable host UI routines** — one per digest slot plus one retry routine
> (+15 min) per slot. Routines persist across session restarts and are visible in the
> Codex / Claude Code routine UI. An optional end-of-day catch-up is also available.
> All routines run `local_routine.py run-due`, which deduplicates via `routine_state.json`
> so the same slot is never published twice.
>
> No local OS schedulers (launchd, cron, systemd) will be used.

Ask in **one prompt** — do not ask for times/timezone without also collecting working hours, retry, and catch-up:

> **Schedule configuration**
> Please provide:
> - **Run times** — e.g. `10:00, 14:00` (comma-separated HH:MM)
> - **Timezone** — e.g. `Europe/London`, `Asia/Shanghai`, `Etc/GMT-1` (default: `Asia/Shanghai`)
> - **Working hours** — e.g. `08:00-18:00` (default: `08:00-19:00`)
> - **Retry routines?** — fires 15 min after each slot if main run missed/failed (default: yes)
> - **End-of-day catch-up?** — fires ~30 min after last slot to retry missed runs (default: yes)

### 3.1 Create the Folder

Ask the user (English): *"Should I create a new Feishu folder named `Slack Daily Digest` to store all daily docs, or do you have an existing folder? If existing, paste the folder URL."*

If Mira and new → use `lark-drive-wiki-skill` `create-folder --name "Slack Daily Digest" --folder-token <root>` and capture the token.

If Codex / Claude Code and new → use Lark CLI through `scripts/lark_doc_client.py` / `lark-cli drive +create-folder`; do not require a custom Lark app for document writing when Lark CLI user auth is available.

### 3.2 Create the Index Doc

Use `scripts/lark_doc_client.py` so Mira keeps `lark-docs-skill` behavior and local mode uses `lark-cli`.

```
Title: Slack Daily Digest · Index
Body:
## This document is auto-maintained by Mira. Daily digests are listed below in reverse chronological order (newest on top). Monitoring scope: all Slack channels the configured user has joined; the channel list refreshes on every run.
## Daily Digest List (newest on top)
```

Move it into the folder through the same document client.

### 3.3 Ask for Schedule

Use the run times, timezone, working hours, retry, and catch-up preferences collected in §3.0.

Persist to `~/.slack-daily-digest/index.json`:

```json
{
  "index_doc_url": "https://www.feishu.cn/docx/...",
  "index_doc_id": "...",
  "folder_token": "...",
  "timezone": "Etc/UTC",
  "schedule": [{"hour": 11, "minute": 0, "timezone": "Etc/UTC", "tz": "+00:00", "window_hours": 19},
               {"hour": 16, "minute": 0, "timezone": "Etc/UTC", "tz": "+00:00", "window_hours": 5}]
}
```

For local mode, also persist `~/.slack-daily-digest/routine.json`:

```json
{
  "timezone": "Etc/UTC",
  "slots": ["11:00", "16:00"],
  "working_hours": {"start": "09:00", "end": "18:00"},
  "catchup_hours": 6,
  "check_interval_minutes": 10,
  "agent": {"type": "auto", "command_template": null}
}
```

### 3.4 Register Recurring Task

For Mira, use the `loop` skill (or platform's scheduled-task mechanism) to register:

- Run `slack-daily-digest run` at each scheduled time.
- Run `slack-daily-digest watchdog` 20 minutes after each scheduled time.

For Codex / Claude Code — **durable host UI routines only. No local OS scheduler. No session-only routines.**

#### Error codes from `setup-scheduler`

| Exit code | Meaning | Action |
|---|---|---|
| `host_unknown` | Not in a Codex or Claude Code session | Stop. Do not create any scheduler. |
| `session_only_routine_not_allowed` | Host detected but does not support durable routines | Stop. Report to user. |
| `host_durable_ui_routine_unavailable` | `mcp__scheduled-tasks__create_scheduled_task` unavailable | Stop. Do not fall back to CronCreate or local OS scheduler. |
| `stable_path_required` | `SLACK_DIGEST_HOME` is under `/tmp` or a test path | Ask user to confirm stable path (default `~/.slack-daily-digest`) before continuing. |
| `scheduler_setup_blocked` | Missing credentials, index, or runner config | Fix the listed items, then re-run. |

#### Step 1 — Validate and get setup request

```bash
python3 scripts/local_routine.py setup-scheduler \
  --slots "<times>" --timezone "<timezone>" --working-hours "<window>"
```

Prints a `scheduler_setup_request` JSON on success. Key fields:

- `host_scheduler` — `"codex"` or `"claude_code"`
- `scheduler_durability` — always `"durable_ui"`
- `host_instructions` — host-specific creation notes (read `host_instructions.create_method`)
- `host_routines` — one descriptor per slot (main)
- `retry_routines` — one descriptor per slot at slot + 15 min
- `optional_catchup_routine` — end-of-day catch-up descriptor
- `local_scheduler_used` — always `false`
- `session_only_routine_used` — always `false`

If `setup-scheduler` exits non-zero, stop and show the error verbatim to the user.

#### Step 2 — Create durable host UI routines

Read `host_instructions.host` from the JSON.

---

##### Step 2A — Codex (`host_instructions.host == "codex"`)

Use `mcp__scheduled-tasks__create_scheduled_task`. All routines are durable and visible in the Codex automation UI.

**Main routines** — for each entry in `host_routines[]`:
```
mcp__scheduled-tasks__create_scheduled_task(
  name        = entry.name,
  description = entry.description,
  command     = entry.command,    # local_routine.py run-due --slot HH:MM --timezone TZ
  cron        = entry.cron,       # e.g. "0 10 * * *"
  env         = entry.env,        # SLACK_DIGEST_HOME + SLACK_DIGEST_PLATFORM
)
```

**Retry routines** — for each entry in `retry_routines[]`:
```
mcp__scheduled-tasks__create_scheduled_task(
  name        = entry.name,       # e.g. "slack-digest-1000-retry"
  description = entry.description,
  command     = entry.command,
  cron        = entry.cron,       # e.g. "15 10 * * *"
  env         = entry.env,
)
```

Example for slots `["10:00", "16:00"]` Europe/London:
```
slack-digest-1000        cron="0 10 * * *"   → main 10:00
slack-digest-1000-retry  cron="15 10 * * *"  → retry 10:00
slack-digest-1600        cron="0 16 * * *"   → main 16:00
slack-digest-1600-retry  cron="15 16 * * *"  → retry 16:00
```

**Optional catch-up** (ask user — see below). After creation record IDs (Step 3).

---

##### Step 2B — Claude Code (`host_instructions.host == "claude_code"`)

Use `mcp__scheduled-tasks__create_scheduled_task`. Scheduled tasks are durable, persist across session restarts, and are visible in the Claude Code Scheduled/Routines UI.

**Do NOT use `CronCreate`.** CronCreate jobs are session-only and auto-expire after 7 days — they are not allowed for production scheduled runs. If `mcp__scheduled-tasks__create_scheduled_task` is unavailable, stop with `host_durable_ui_routine_unavailable` — do not fall back to CronCreate, session-only jobs, launchd, or any local OS scheduler.

**Stable path check:** Before creating any scheduled task, confirm `SLACK_DIGEST_HOME` is not under `/tmp` or a test directory. If it is, stop and ask the user to confirm a stable path (default `~/.slack-daily-digest`). Do not create durable tasks that point to `/tmp`.

**Main routines** — for each entry in `host_routines[]`:
```
mcp__scheduled-tasks__create_scheduled_task(
  name        = entry.name,        # e.g. "slack-digest-1000"
  description = entry.description,
  command     = entry.command,     # local_routine.py run-due --slot HH:MM --timezone TZ
  cron        = entry.cron,        # e.g. "0 10 * * *"
  env         = entry.env,         # SLACK_DIGEST_HOME + SLACK_DIGEST_PLATFORM
)
```

**Retry routines** — for each entry in `retry_routines[]`:
```
mcp__scheduled-tasks__create_scheduled_task(
  name        = entry.name,        # e.g. "slack-digest-1000-retry"
  description = entry.description,
  command     = entry.command,     # same run-due command; skips silently if slot succeeded
  cron        = entry.cron,        # e.g. "15 10 * * *"
  env         = entry.env,
)
```

Confirm to the user that tasks are durable and visible in the Claude Code Scheduled/Routines UI.

> **⚠️ One-time permission approval required (Claude Code)**
>
> Claude Code scheduled tasks run with `permissionMode: default`. The first time a task fires,
> it may pause and prompt for Bash/Write tool approval before executing `local_routine.py run-due`.
>
> **Required action after creating routines:**
> 1. Open the **Scheduled** section in the Claude Code sidebar.
> 2. Find the first digest task (e.g. `slack-digest-HHmm`).
> 3. Click **Run now**.
> 4. When prompted, approve **Bash** and **Write** tools.
> 5. Tool approvals are stored on the task and auto-applied to all future scheduled runs.
>
> **Do not call scheduled setup fully verified** until a task has actually executed
> `local_routine.py run-due` and a Lark digest doc URL appears in `routine_state.json`.
>
> **Alternative (pre-approve via settings):** Add the following to the project
> `.claude/settings.local.json` inside the `permissions.allow` array so that scheduled
> task sessions (which run from cwd `~/.claude`) auto-approve without prompting:
> ```json
> "Bash(SLACK_DIGEST_HOME=<STATE_DIR> SLACK_DIGEST_PLATFORM=local_agent python3 <SKILL_DIR>/scripts/local_routine.py run-due *)",
> "Bash(<SKILL_DIR>/scripts/local_routine.py *)",
> "Write(<STATE_DIR>/**)"
> ```
> Replace `<STATE_DIR>` with `SLACK_DIGEST_HOME` value and `<SKILL_DIR>` with the skill path.

**Jitter and timing:** Scheduled tasks apply a small deterministic delay (up to ~10 min) at
dispatch time. The retry routine (+15 min) and optional catch-up routine handle any slots that
fire late or miss their window. Do not treat a delayed first fire as a failure.

**Optional catch-up** (ask user — see below). After creation record IDs (Step 3).

---

#### Catch-up routine (all hosts — create if user opted in during §3.0 schedule configuration)

Create a durable routine from `optional_catchup_routine` using the same method as above (Step 2A or 2B). Do not ask the user again — catch-up preference was already collected in §3.0.

---

#### Step 3 — Record routine IDs and report

```bash
python3 scripts/local_routine.py set-backend --backend host_routine \
  --durability durable_ui \
  --routine-ids "<main-id-1>,<main-id-2>" \
  --retry-ids "<retry-id-1>,<retry-id-2>" \
  [--catchup-ids "<catchup-id>"]
```

Do not call `set-backend` unless durable routine creation succeeded and IDs were returned.

#### Validation before reporting success

Report scheduler setup success only after **all** of the following are true:
- `mcp__scheduled-tasks__create_scheduled_task` (or Codex equivalent) returned task IDs
- `set-backend` completed without error
- `routine.json` records `scheduler_durability: "durable_ui"` and the routine IDs
- No local scheduler (launchd / cron / systemd) was created
- No CronCreate job was created (not even session-only)
- No session-only routine was created
- At least one task has **actually executed** `local_routine.py run-due` and produced a Lark doc URL in `routine_state.json` (confirmed via "Run now" or a scheduled fire)

If a routine was created but has never executed end-to-end, report setup as **pending verification**, not success. Instruct the user to find the task in the Scheduled/Routines UI, click "Run now", and approve Bash/Write tools if prompted.

#### Final report (keep short)

```
host: codex | claude_code
scheduler backend: durable host UI routine
main routine IDs: [...]
retry routine IDs: [...]
catch-up routine ID: <id> | none
timezone: <TZ>
working hours: HH:MM-HH:MM
SLACK_DIGEST_HOME: <path>
local scheduler used: no
CronCreate used: no
session-only routine used: no
```

#### Shared routine logic

All routines invoke `local_routine.py run-due --slot HH:MM --timezone TZ`, which:
- Loads `routine_state.json` — skips immediately if this date+slot already succeeded
- Acquires `routine.lock` — prevents overlapping runs
- Runs the full pipeline: pull Slack → build digest JSON → agent synthesizes `final_*.md` → publish to Lark
- Marks `success` only after a Lark doc URL is confirmed in `result_*.json`
- Marks `transient_error` on network/API failures — retried by the +15 min retry routine
- Marks `credential_error` on auth failure — stops retrying, notifies user
- Marks `skipped_missed_window` when the catch-up window expires

---

## 4. Phase C — User-Cache Refresh (weekly)

Run `scripts/refresh_users_cache.py`:

- If `users_cache.json` mtime > 7 days → call `users.list` paginated (Tier 2, sleep 1s between pages) and rewrite cache.
- Otherwise skip.

This step is automatic at the start of every Daily Run.

---

## 5. Phase D — Daily Run

Steps 1–8 below mirror the proven pipeline. All scripts live in `scripts/`.

| Step | Action | Script |
|---|---|---|
| 1 | List all conversations the user joined | `scripts/list_channels.py` |
| 2 | Compute time window from schedule | `scripts/run_digest.py` (inline) |
| 3 | Pull `conversations.history` per channel (sleep 0.3s, Tier 3) | `scripts/pull_history.py` |
| 4 | Resolve user IDs → names; replace `<@Uxxx>` mentions; identify BytePlus owner per channel | `scripts/build_digest.py` |
| 5 | AI synthesis — Executive Summary, Highlights, TODO, Pipeline, Risks, By-Channel (full message text, **never truncate**), Statistics | LLM call inside the conversation |
| 6 | Create per-day Feishu doc `Slack Daily Digest · YYYY-MM-DD`; move to folder; if doc already exists for today (16:00 run), `edit-inplace` replace the placeholder section | `scripts/lark_doc_client.py` |
| 7 | **Pin** the new entry to the **top** of the index list (insert_before the current first list item, NOT insert_after the title) | `scripts/lark_doc_client.py` |
| 8 | Lark IM notify the user | `scripts/notify_lark.py` |

### 5.1 Time-Window Calc

```python
import datetime, calendar
now_utc = datetime.datetime.utcnow()
window_hours = config["window_hours"]  # 19 for 11:00, 5 for 16:00
oldest = calendar.timegm((now_utc - datetime.timedelta(hours=window_hours)).timetuple())
latest = calendar.timegm(now_utc.timetuple())
```

### 5.2 v4 Synthesis Spec — Mandatory Sections

The digest MUST contain, in order:

1. **🎯 Executive Summary** — 3-5 bullets, each with 🔴/🟡/🟢 + Owner + concrete action
2. **📌 Highlights** — 6-10 cross-channel one-liners
3. **✅ TODO Backlog** — table: `Priority | Owner | Item | Deadline | Source channel`
4. **📈 Business Pipeline** — table: `Partner | Stage/Amount | Status | Owner | Health`
5. **⚠️ Risk Signals** — bulleted with channel + risk
6. **🗂️ By Channel** — for each active channel, four sub-blocks:
   - **📖 Context** — 2-4 sentences
   - **💬 Full Messages** — every message verbatim, newlines normalized to ` / ` (slash-space). **No truncation.**
   - **🎯 Next Steps** — at least one P0-P2 with named Owner + Deadline
   - **Risk** — one line, 🔴/🟡/🟢 prefix
7. **📝 Statistics** — top channels, top contributors, identified BytePlus owners
8. Trailing placeholder for the next intra-day run: `## 🕙 16:00 Update (placeholder, to be filled)` — only on the morning run

### 5.3 Pin-to-Top Rule (CRITICAL)

The natural `insert_after` against the index title appends to the bottom of the list (because all list items are siblings of the title). The correct anchor is the **current first list item**:

```python
# Read index doc, find first "- **YYYY-MM-DD**" line
# Use insert_before with that line as the anchor
edits = [{
    "mode": "insert_before",
    "selection_with_ellipsis": "- **<previous-newest-date>** · [Slack Daily Digest · ...]",
    "markdown": "- **<today>** · [Slack Daily Digest · <today>](<new-url>)"
}]
```

If the list is empty, fall back to `insert_after` against the title (only happens for the first-ever entry).

---

## 6. Phase E — Watchdog (T+20min)

Triggered 20 minutes after each scheduled run.

```bash
python3 ~/.claude/skills/slack-daily-digest/scripts/watchdog.py --date <today> --slot <11:00|16:00>
```

Watchdog checks:

1. **Doc existence** — read the index, look for `<today>`'s entry. Missing → fail.
2. **Doc content** — read the doc body. Verify all 7 mandatory sections (§5.2) are present.
3. **Section completeness** — for the slot in question (11:00 → main body; 16:00 → 16:00 section must not contain the placeholder text "placeholder, to be filled").

On failure:
- Read `~/.slack-daily-digest/runs/<today>/error.log` if it exists; otherwise inspect the latest pull/build artifacts.
- Diagnose root cause (network, token expired, rate-limit, doc-edit ambiguity).
- **Self-retry**: rerun from the failing step. Token expired → notify user via IM and stop. All other failures → up to 3 retries with backoff `[60s, 300s, 900s]`.
- After each retry, re-invoke watchdog. Loop until success or until the token-expired terminal condition.

On success:
- Append a one-line success note to `~/.slack-daily-digest/runs/<today>/watchdog.log`.
- Do **not** notify the user on success (only failure / recovery).

---

## 6.5 Local Routine Catch-Up

For Codex / Claude Code local mode, `scripts/local_routine.py run-due` owns schedule catch-up:

- One success per date + slot.
- If the computer was off/asleep at the scheduled time, run automatically on the next active check when current time is inside working hours and within `catchup_hours` after the scheduled slot.
- If a run fails due to transient errors, retry on future routine ticks while still inside the catch-up window.
- If credentials are invalid/expired, stop retrying and notify the user clearly.
- If the catch-up window expires, mark the slot as `skipped_missed_window` and do not create a stale digest next day.
- Use `~/.slack-daily-digest/routine.lock` to prevent overlapping runs.

The local routine invokes `scripts/run_digest.py`. One-off local mode pulls Slack history, builds `digest_*.json`, writes a host-agent handoff for synthesizing `final_*.md` from `references/digest-template.md`, publishes via `LarkDocClient` after `final_*.md` exists, updates the index newest-on-top, and writes `~/.slack-daily-digest/runs/<date>/result_<slot>.json`.

---

## 7. Phase F — Lark IM Notification

After successful daily run, push to the configured user's Lark IM:

```bash
python3 ~/.claude/skills/slack-daily-digest/scripts/notify_lark.py \
  --user-email "<from credentials>" \
  --doc-url "<today's doc URL>" \
  --highlights "@~/.slack-daily-digest/runs/<today>/highlights.md"
```

The notify script:
1. Resolves email → open_id via Lark Contact API.
2. Sends an interactive card with:
   - Title: `🔔 Slack Daily Digest · <today HH:MM configured timezone>`
   - Top 3 Highlights
   - Top 3 TODO items with owner + deadline
   - "Open Full Doc" button → doc URL

---

## 8. Error Handling Reference

| Error | Action |
|---|---|
| Slack `ratelimited` | sleep 60s, retry up to 3× |
| Slack `invalid_auth` / `token_revoked` | Append to error.log, IM the user "Slack token expired, please reconfigure", **stop**. |
| `users.info` fails for one user | Fallback to `User(<id>)`, do not block the run. |
| Lark `99991663/4/5/8` or "token expire" | The agent harness's token-refresh hook handles this — do NOT re-implement here. |
| Lark `edit-inplace` validation 1101 (locator not found) | Re-read doc with `--output-format markdown`, recompute the exact anchor (watch for full-width vs half-width punctuation), retry. |
| Lark doc create timeout | Save raw markdown to `~/.slack-daily-digest/runs/<today>/backup.md` and IM the user. |

---

## 9. Cookbook — Common Operations

### Reconfigure schedule
```bash
python3 ~/.claude/skills/slack-daily-digest/scripts/save_credentials.py --reschedule "11:00,16:00"
```

### Force a one-off run for an arbitrary window
```bash
python3 ~/.claude/skills/slack-daily-digest/scripts/run_digest.py --oldest <epoch> --latest <epoch>
```

### Backfill a missed day
```bash
python3 ~/.claude/skills/slack-daily-digest/scripts/run_digest.py --date 2026-05-04 --slot 11:00
```

---

## 10. Files in This Skill

```
slack-daily-digest/
├── SKILL.md                          # this file
├── scripts/
│   ├── save_credentials.py           # encrypt + persist creds
│   ├── refresh_users_cache.py        # weekly users.list refresh
│   ├── list_channels.py              # users.conversations
│   ├── pull_history.py               # conversations.history per channel
│   ├── build_digest.py               # ID resolution + owner detection
│   ├── run_digest.py                 # orchestrator (Steps 2-7)
│   ├── platform.py                   # Mira vs local-agent detection
│   ├── lark_doc_client.py            # Mira docs / local Lark CLI abstraction
│   ├── setup_lark_cli.py             # local Lark CLI readiness helper
│   ├── local_routine.py              # local schedule + missed-run catch-up runner
│   ├── watchdog.py                   # T+20min verification + self-retry
│   ├── notify_lark.py                # Lark IM notification
│   └── lark_helpers.py               # shared: token, email→open_id, doc edit
└── references/
    ├── slack-app-setup.md            # extended Slack onboarding docs
    ├── lark-bot-setup.md             # extended Lark onboarding docs
    └── digest-template.md            # full v4 synthesis template
```
