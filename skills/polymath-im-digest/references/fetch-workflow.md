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

## Conversation Discovery (message-first)

> The local wiki customer list is **not** the starting point. Discover conversations from Lark activity first; cross-reference the wiki afterward for context enrichment only.

### Step 1 — Collect all P2P messages from yesterday

P2P discovery does not require enumerating contacts — search across all P2P conversations at once:

```bash
lark-cli im +messages-search \
  --chat-type p2p \
  --start "$START_TIME" --end "$END_TIME" \
  --exclude-sender-type bot \
  --page-all \
  --format json \
  --as user
```

Group the returned messages by `chat_id` to reconstruct per-conversation threads. Each distinct `chat_id` in the result is a P2P thread that was active yesterday.

### Step 2 — Enumerate all joined group chats and probe for activity

```bash
# Page through all joined groups, newest-activity first
lark-cli im +chat-search \
  --sort-by update_time_desc \
  --page-size 100 \
  --format json \
  --as user
# Repeat with --page-token until has_more=false (cap at 500 groups)
```

For every group, batch-probe for yesterday's messages in parallel (batches of 20):

```bash
lark-cli im +chat-messages-list \
  --chat-id <oc_xxx> \
  --start "$START_TIME" --end "$END_TIME" \
  --sort asc --page-size 1 \
  --format json --as user
# page-size 1 for probe; re-fetch with page-size 50 in Phase 1 if active
```

Error handling:

| Error | Action |
|---|---|
| `99991400` / `403` | Log "no access: <chat_name>"; skip |
| 0 messages | Skip silently |
| Rate limit (`99991663`) | Wait 1 s; retry once |

### Step 3 — Wiki cross-reference (enrichment only)

After the user confirms the scan list, cross-reference each active conversation against `$LOCAL_WIKI_ROOT/wiki/entities/customers/*.md` using the `lark_chat` field, person name (for P2P), or fuzzy chat-name match. Attach existing customer/person context for richer analysis. Conversations with no wiki match are flagged as **potential new customer or contact** in the digest.

### Step 4 — User provides additional conversations

The user may add extra group chats (`oc_xxx` or name) or P2P contacts (name or `ou_xxx`) at confirmation time. Resolve names via `+chat-search --keyword` (groups) or `lark-cli contact +search` (P2P).

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
