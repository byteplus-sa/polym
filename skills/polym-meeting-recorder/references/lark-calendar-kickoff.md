# Lark Calendar Kickoff Workflow

This workflow replaces Syncore note-taker's default Google Calendar kickoff path.

## Goal

When the user says "start recording" without a meeting title, identify the current meeting using Lark Calendar, then ask for confirmation before starting Syncore recording.

## Query Window

Use a now ± 10 minute window:

```bash
# macOS
START=$(date -v-10M +"%Y-%m-%dT%H:%M:%S+08:00")
END=$(date -v+10M +"%Y-%m-%dT%H:%M:%S+08:00")

lark-cli calendar +agenda \
  --start "$START" \
  --end "$END" \
  --format json \
  --as user
```

```bash
# Linux
START=$(date -d "10 minutes ago" +"%Y-%m-%dT%H:%M:%S+08:00")
END=$(date -d "10 minutes" +"%Y-%m-%dT%H:%M:%S+08:00")
```

## Candidate Rules

### 0 Candidates

Ask in the user's chat language:

```text
What should I call this meeting, and who's joining?
```

Do not mention calendar lookup internals.

### 1 Candidate

Ask for confirmation:

```text
Looks like you are in "<title>" with <attendees>. Start recording with that name, or call it something else?
```

Wait for explicit confirmation before calling Syncore.

### Multiple Candidates

Show a numbered picker:

```text
I found a few meetings around now:
1. <title> · <HH:MM-HH:MM> · <attendees>
2. <title> · <HH:MM-HH:MM> · <attendees>

Which meeting are you in? Reply with 1, 2, or a new name.
```

If the user replies with a number, carry over attendees from that event.
If the user replies with free text, use it as the title.

## Attendee Extraction

Prefer display names. If the agenda output only includes emails or open IDs, keep the title and omit participants rather than guessing.

Never pass `null` as participants to Syncore. Use `[]` when unknown.

## Silent Fallback

If the Lark command errors, times out, or returns malformed data, ask only:

```text
What should I call this meeting, and who's joining?
```

Do not say "Lark Calendar failed" unless the user asks why you need the title.

