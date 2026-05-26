# slack-daily-digest

A [Mira](https://mira.bytedance.com/) / Codex / Claude Code skill that turns your Slack workspace into an AI-synthesized **daily intelligence digest** in Feishu (Lark) docs — Highlights, TODO backlog, business pipeline, risks, by-channel breakdown — pinned to a single index doc and pushed to you via Lark IM.

---

## ✨ Features

- **One-time onboarding** walks you through creating a Slack User OAuth App and a Lark Custom Bot, then stores credentials locally (`~/.slack-daily-digest/credentials.json`, mode `0600`).
- **Unified index doc** in Feishu — every daily digest is **pinned to the top** of the list.
- **Twice-daily synthesis** (default 11:00 / 16:00 in the configured timezone) covering recent messages with:
  - 🎯 Executive Summary (P0/P1/P2 prioritized)
  - 📌 Highlights · ✅ TODO · 📈 Pipeline · ⚠️ Risk Signals
  - 🗂️ By-Channel verbatim transcripts (no truncation, no ellipsis)
  - 📝 Statistics + identified BytePlus / ByteDance owners
- **Self-healing watchdog** runs T+20min after each scheduled slot. Verifies all required sections exist; on failure self-retries with `[60s, 300s, 900s]` backoff up to 3 times, then escalates.
- **Local-agent routine runner** for Codex and Claude Code using Lark CLI, with missed-run catch-up while the computer is awake and online.

## Platform support

| Platform | Lark docs | Scheduling | Retry/catch-up |
|---|---|---|---|
| Mira | Built-in Lark doc skills | Mira scheduled task | Mira watchdog + retry |
| Codex | Local Lark CLI | Local routine runner | Catch-up on next active check |
| Claude Code | Local Lark CLI | Local routine runner | Catch-up on next active check |

For Codex / Claude Code local mode, scheduled runs depend on your local computer. The routine runner checks for due or missed slots while the computer is awake and online. If the computer is asleep/off at the scheduled time, the digest will catch up automatically after wake/login if it is still within the configured working-hours and catch-up window.
- **Lark IM card notification** with Highlights + TODO summary + "Open Full Digest" button.

One-off local E2E uses the current host agent for final digest synthesis through a handoff file. If you later enable unattended scheduled runs, setup can ask for an unattended synthesis backend at that point.

---

## 📦 Install

This is a Mira / Codex / Claude Code skill. Drop the contents of this repo into your skills directory:

```bash
git clone https://github.com/<your-org>/slack-daily-digest.git \
  ~/.claude/skills/slack-daily-digest
```

Then in your next conversation, ask the agent:

> "Set up Slack daily digest"

The skill will guide you through Slack App + Lark Bot onboarding.

---

## 🔧 Prerequisites

| Requirement | Why |
|---|---|
| Python 3.9+ | Helper scripts |
| `curl`, `jq` | API calls + JSON parsing |
| A Slack workspace where you can install a custom app | Read channel history |
| A Feishu / Lark tenant where you can publish a custom app | Write docs + send IM |
| Mira Lark document skills, or `lark-cli` for Codex / Claude Code local mode | Doc CRUD + folder ops |

See [`references/slack-app-setup.md`](references/slack-app-setup.md) and [`references/lark-bot-setup.md`](references/lark-bot-setup.md) for credential creation.

---

## 🚀 Quick Start

After installing, the skill auto-runs **Phase A (Onboarding)** on first invocation:

1. Slack: create app → add User Token Scopes → install → paste `xoxp-...`
2. Lark: create app → add scopes → publish → paste `App ID` + `App Secret` + your work email
3. Index doc: pick a parent folder (or create new) → confirm daily run time
4. Mira registers platform scheduled tasks; Codex / Claude Code install the local routine runner after Lark CLI readiness is confirmed

From then on, every scheduled slot:

```
slack-daily-digest run --slot 11:00
slack-daily-digest watchdog --slot 11:00   # T+20min
```

Local mode stores routine state in `~/.slack-daily-digest/routine.json` and `~/.slack-daily-digest/routine_state.json`. On macOS the installer writes `~/Library/LaunchAgents/com.byteplus.slack-daily-digest.plist`; on Linux it uses a user-level systemd timer when available.

---

## 🗂️ Repo Layout

```
SKILL.md                          # Skill manifest (Mira-compatible)
scripts/
├── save_credentials.py           # Persist Slack/Lark creds + schedule
├── refresh_users_cache.py        # Refresh users.list cache (Tier 2, 7-day TTL)
├── list_channels.py              # users.conversations paginated list
├── pull_history.py               # conversations.history per channel + filters
├── build_digest.py               # Resolve mentions, BytePlus owner detection
├── lark_helpers.py               # tenant_token / email→open_id / doc CRUD
├── lark_doc_client.py            # Mira doc skills / local Lark CLI abstraction
├── local_routine.py              # local schedule + missed-run catch-up runner
├── platform.py                   # Mira vs local-agent detection
├── setup_lark_cli.py             # local Lark CLI readiness helper
├── run_digest.py                 # Orchestrator (Steps 0-4 + agent handoff)
├── watchdog.py                   # T+20min self-healing checker
└── notify_lark.py                # IM card with Highlights + TODO
references/
├── slack-app-setup.md            # Step-by-step Slack App guide
├── lark-bot-setup.md             # Step-by-step Lark Bot guide
└── digest-template.md            # Synthesis template v4 (Hard Rules + rubric)
```

---

## 🔐 Security

- Credentials live **only** in `~/.slack-daily-digest/credentials.json` with mode `0600`.
- The Lark `tenant_access_token` is cached for 90 minutes in `~/.slack-daily-digest/.lark_tenant_token`.
- The skill never sends credentials over the wire to anything other than the Slack and Lark APIs.
- `.gitignore` excludes all runtime data — verify before committing.

If your Slack token is revoked or rotated, re-run:

```bash
python3 scripts/save_credentials.py --slack-token "xoxp-..."
```

---

## ⚠️ Hard Rules (encoded in `references/digest-template.md`)

- ❌ **Never** truncate a message with `[:N]`.
- ❌ **Never** collapse long messages into ellipsis.
- ❌ **Never** keep only a summary while dropping the original text.
- ✅ Filter `channel_join`, `channel_leave`, pure-emoji replies, pure greetings.
- ✅ Allowed to merge consecutive messages from the same speaker for compactness.

---

## 🤝 Contributing

PRs welcome. Please:

1. Strip any real credentials, doc URLs, channel IDs, or user names from logs/screenshots.
2. Test the onboarding flow end-to-end on a fresh `~/.slack-daily-digest/` directory.
3. Update `CHANGELOG.md` with user-visible changes.

---

## 📜 License

[MIT](LICENSE)
