# Fetch Workflow — IM Message Retrieval

## Date Calculation

```bash
# macOS
YESTERDAY=$(date -v-1d +%Y-%m-%d)
START_TIME="${YESTERDAY}T00:00:00+08:00"
END_TIME="${YESTERDAY}T23:59:59+08:00"

# Linux / CI
YESTERDAY=$(date -d yesterday +%Y-%m-%d)
START_TIME="${YESTERDAY}T00:00:00+08:00"
END_TIME="${YESTERDAY}T23:59:59+08:00"
```

Override with `--date YYYY-MM-DD` if user specifies a different date.

---

## Chat Discovery

### Method A — From local wiki (preferred)

```bash
# Scan all customer pages for lark_chat field
grep -r "^lark_chat:" $LOCAL_WIKI_ROOT/wiki/entities/customers/ \
  | sed 's/.*lark_chat: //'
```

For each non-empty `lark_chat` value:
- If it looks like `oc_xxx` → use directly as chat_id
- If it's a chat name → resolve via `+chat-search`

### Method B — Chat search by name

```bash
lark-cli im +chat-search \
  --keyword "<customer_name>" \
  --format json \
  --as user
# Returns: chat_id, name, member_count, description
```

Pick the best match (exact name match preferred; ask if ambiguous).

### Method C — User provides

Accept chat_ids or names as comma-separated input. Resolve names via Method B.

---

## Fetch Messages Per Chat

```bash
# Basic fetch — yesterday's messages
lark-cli im +chat-messages-list \
  --chat-id <oc_xxx> \
  --start "$START_TIME" \
  --end "$END_TIME" \
  --sort asc \
  --page-size 50 \
  --format json \
  --as user
```

### Pagination

If the response contains `"has_more": true`:
```bash
lark-cli im +chat-messages-list \
  --chat-id <oc_xxx> \
  --start "$START_TIME" \
  --end "$END_TIME" \
  --sort asc \
  --page-size 50 \
  --page-token "<page_token from previous response>" \
  --format json \
  --as user
```

Repeat until `has_more` is false. Cap at 500 messages per chat (10 pages); warn user if exceeded.

### Message types to process

| Type | Action |
|---|---|
| `text` | Extract full content |
| `post` | Extract rich text content |
| `interactive` | Extract visible text from card body if available; otherwise skip |
| `image` | Log as `[Image]` placeholder |
| `file` | Log as `[File: <filename>]` placeholder |
| `audio` / `video` | Log as `[Media]` placeholder |
| `sticker` | Skip |
| `merge_forward` | Extract nested messages recursively |

### Sender filtering

Skip messages from bots (`sender_type: bot`) unless they contain meaningful automated content (e.g., incident alerts).

---

## Raw Snapshot Format

Write to `$LOCAL_WIKI_ROOT/raw/chat-<customer-slug>-<YESTERDAY>.md`:

```markdown
---
source: lark-im
chat_id: oc_xxx
chat_name: <name>
customer: <slug>
date: <YESTERDAY>
fetched_at: <ISO timestamp>
message_count: <N>
---

# Raw Chat Snapshot — <chat_name> — <YESTERDAY>

[HH:MM] <sender_name>: <content>
[HH:MM] <sender_name>: <content>
...
```

Rules:
- Times in `HH:MM` (UTC+8)
- Sender display name (not open_id)
- Content verbatim for text messages; placeholder tags for media
- Append if file already exists (don't overwrite)

---

## Error Handling

| Error | Cause | Fix |
|---|---|---|
| `99991400` / `403` | No access to chat | Skip this chat; log `"no access: <chat_name>"` |
| `"has_more": true` after 10 pages | Very active chat | Warn user; stop at page 10; note truncation in raw snapshot header |
| `chat_id not found` from `+chat-search` | Chat doesn't exist or not visible | Ask user to verify the chat name |
| Empty response (0 messages) | No activity yesterday | Skip silently; include in "no activity" list |
| Rate limit (`99991663`) | Too many requests | Wait 1 second; retry once |
