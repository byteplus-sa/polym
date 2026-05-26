# Codex Routine Setup

This skill should not implement its own scheduler. When the user asks to run IM
digest every day, help them create a Codex routine / automation that invokes the
normal interactive skill prompt on a schedule.

## User Intents

Examples:

- `每天早上 9 点自动跑 IM digest`
- `帮我创建一个每天整理昨天 IM 的 Codex routine`
- `每天上班前把昨天的群消息总结成飞书文档`

## Routine Prompt

Use a self-contained prompt like:

```text
Run polym-im-digest for yesterday. Discover active Lark P2P and group
conversations, apply the local blacklist, ask only for required confirmations
if this routine is configured to run in a thread that allows user input, create
the Feishu digest doc, and write approved knowledge-base updates through the
normal polym-im-digest workflow. Return the doc URL, scanned chat/message
counts, P0/P1 items, owner/deadline gaps, and knowledge-base write results.
```

For unattended routines, add:

```text
If a confirmation would normally be needed, use the safest default: skip local
wiki creation if no wiki exists, create the Feishu doc in the personal drive
root, and do not include conversations that are blacklisted or inaccessible.
```

## Suggested Schedule

Use the user's requested time when provided. Interpret relative phrases such as
`每天早上 9 点` or `weekday morning` in the user's local timezone as reported by
the Codex environment / local machine, not a hard-coded timezone.

If the user did not provide a time, ask once:

```text
What local time should the IM digest routine run? For example: weekdays 9:00,
or every day 8:30.
```

Recommendations:

- weekday morning at the user's chosen local time for workday review
- daily morning at the user's chosen local time if they want weekend coverage

Only mention a concrete timezone when the runtime exposes it or the user names
one. Prefer labels like `09:00 local time` over assuming `Asia/Shanghai`.

## Codex Automation Guidance

When running inside Codex with automation tools available, create a Codex
automation rather than writing cron files or local scheduler code inside the
skill repository.

Use these fields conceptually:

- name: `Daily IM Digest`
- kind: `cron`
- schedule: daily or weekday at the user's requested local time
- prompt: the routine prompt above
- workspace: the current polym workspace if required by the Codex environment

If automation tools are not available in the current runtime, give the user the
routine prompt and schedule in plain text so they can create it in Codex.

## Boundaries

- Do not add APScheduler, cron wrappers, daemon code, or long-running scheduler
  logic to `polym-im-digest`.
- Do not add self-run environment contracts or local scheduler modes.
- The skill remains a single-run workflow; Codex owns recurrence.
