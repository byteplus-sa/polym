# Changelog

All notable changes to this skill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed
- `SKILL.md` §3.0: Combined all schedule configuration into one prompt (run times, timezone, working hours, retry routines, catch-up) — previously only asked for times/timezone separately, leaving working hours to be collected later.
- `SKILL.md` §3.3: Removed standalone "Ask for Schedule" prompt; now uses preferences already collected in §3.0.
- `SKILL.md` §3.4 Step 2B (Claude Code): Replaced `CronCreate` with `mcp__scheduled-tasks__create_scheduled_task` as the default backend. CronCreate is session-only and auto-expires; the new default uses durable tasks visible in the Claude Code Scheduled/Routines UI.
- `SKILL.md` §3.4: Added `host_durable_ui_routine_unavailable` error code for when `mcp__scheduled-tasks__create_scheduled_task` is unavailable. Skill now stops rather than falling back to CronCreate or local OS scheduler.
- `SKILL.md` §3.4: Stable path check before creating durable tasks — stops if `SLACK_DIGEST_HOME` is `/tmp` or a test directory and asks user to confirm a stable path.
- `SKILL.md` §3.4: Catch-up routine no longer asks a second time — preference is taken from §3.0.
- `SKILL.md` §3.4 Validation / Final report: Added `CronCreate used: no` and `working hours` to final report; updated validation to assert no CronCreate job was created.
- `scripts/platform.py`: Claude Code descriptor updated — `routine_api` → `mcp__scheduled-tasks__create_scheduled_task`, `create_method` → `mcp_scheduled_tasks`. Notes updated to prohibit CronCreate and document `host_durable_ui_routine_unavailable` fallback stop.

## [1.2.0] - 2026-05-22

### Changed
- `platform.py`: Claude Code host descriptor updated — `session_persistent` → `True`, `ui_visible` → `True`, `create_method` → `"cron_create_durable"`, new `durability: "durable_ui"` field. Notes now require `durable=True` and forbid session-only or local-OS fallback. Generic-local-terminal descriptor stripped to a bare unknown-host stub (no longer surfaces local OS install instructions).
- `local_routine.py` `setup_scheduler()`: new `host_unknown` error when host is not Codex or Claude Code; new `session_only_routine_not_allowed` error when host does not support durable routines; `scheduler_durability: "durable_ui"` added to request output; `local_scheduler_used: false` and `session_only_routine_used: false` enforcement flags added.
- `local_routine.py` `set_backend()`: new `--durability durable_ui` argument; saves `scheduler_durability` to `routine.json`; final report fields renamed to `main_routine_ids`, `scheduler_backend: "durable host UI routine"`, `slack_digest_home`, plus explicit `local_scheduler_used: false` and `session_only_routine_used: false`.
- `SKILL.md` §3.4: removed session-only CronCreate path and all local OS fallback language. Step 2B now requires `CronCreate(durable=True)` and stops with `host_durable_routine_unavailable` if unavailable. Error code table added. Final report format defined. `set-backend` call updated to include `--durability durable_ui`.
- `SKILL.md` platform matrix: added Durability column; updated Codex/Claude Code rows to "Durable UI".

## [1.1.0] - 2026-05-22

### Fixed
- `watchdog.py`: replaced hardcoded `python3.11 -m lark_docs` (Mira-only) with `lark-cli docs +fetch` so watchdog works in Claude Code / Codex local mode. Added `_lark_cli()` resolver (honours `LARK_CLI_PATH` env var, falls back to `/opt/homebrew/bin/lark-cli`, then `lark-cli`). Added `_extract_markdown()` to parse the JSON envelope returned by `lark-cli docs +fetch`. Removed the dead `python3.11` fallback re-read path.

### Changed
- Local OS scheduler (launchd / systemd / cron) removed. Only Codex and Claude Code host routines are supported. `install` and `uninstall` commands exit with a clear error message.
- `setup-scheduler` emits `scheduler_setup_request` JSON for CronCreate / Codex scheduled-tasks; validates that `SLACK_DIGEST_HOME` is not under `/tmp` before creating durable routines.
- Platform detection plus a Lark document client abstraction for Mira and local Codex / Claude Code runs.
- Local Lark CLI readiness setup and a local routine runner with missed-run catch-up, working-hours protection, locking, and per-slot retry state under `~/.slack-daily-digest/`.

## [1.0.0] - 2026-05-07

### Added
- Initial public release.
- Phase A onboarding flow for Slack User OAuth App + Lark Custom Bot.
- Phase B index doc creation with user-configurable daily schedule.
- Phase C 7-day-TTL Slack `users.list` cache refresh.
- Phase D twice-daily digest synthesis with Highlights / TODO / Pipeline / Risk / By-Channel sections.
- Phase E T+20min self-healing watchdog with `[60s, 300s, 900s]` backoff.
- Phase F Lark IM card notification with "Open Full Digest" deep link.
- BytePlus / ByteDance owner-identification cascade (suffix → email domain → title keywords → cache fallback).
- "Pin to top" rule for the index doc using `insert_before` against the current first list item.
