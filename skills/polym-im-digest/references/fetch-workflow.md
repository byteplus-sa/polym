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

## Local Blacklist

Resolve the blacklist once before conversation discovery:

1. If `LOCAL_WIKI_ROOT` is valid:
   `$LOCAL_WIKI_ROOT/config/polym-im-digest-blacklist.json`
2. Otherwise:
   `~/.config/polym/im-digest/blacklist.json`
3. Missing file means an empty blacklist.

Blacklist schema and management commands are defined in
[`blacklist.md`](blacklist.md).

Apply the blacklist in two places:

- Before probing group activity: skip any group whose `chat_id` or exact `name`
  appears in `groups`.
- Immediately after P2P discovery: drop any P2P thread whose `chat_id`,
  `chat_partner.open_id`, or exact partner display name appears in `p2p`.

Do not fetch Phase 1 messages, write raw snapshots, analyze, create digest
sections, or write wiki entries for blacklisted conversations.

P2P limitation: current `lark-cli im +messages-search --chat-type p2p` does not
support negative filters. The blacklist therefore prevents blacklisted P2P
threads from all downstream processing, but the global discovery query may still
return them before they are discarded.

---

## Conversation Discovery (message-first)

> The local wiki customer list is **not** the starting point. Discover conversations from Lark activity first; cross-reference the wiki afterward for context enrichment only.

### Steps 1 & 2 — Run in parallel

Fire both branches at the same time; merge before Step 3.

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

Filter grouped P2P threads against the local blacklist before merging with group
activity. Count discarded threads as `skipped_by_blacklist`; do not include their
names in the user-facing scan list.

### Step 2 — Enumerate ALL joined group chats and probe for activity

> Covers every group the user is in — including new customer groups not yet in the local wiki.

```bash
# Page through all joined groups, newest-activity first
lark-cli im chats list \
  --as user \
  --page-all --page-limit 5 \
  --params '{"page_size":100,"sort_type":"ByActiveTimeDesc"}' \
  --format json
# page-limit 5 caps discovery at 500 groups.
```

Implementation note: use `im chats list` for full joined-group enumeration.
`im +chat-search` is only for lookup by keyword or member IDs; current
`lark-cli` rejects an empty search with `--query and --member-ids cannot both
be empty`.

For every group, batch-probe for yesterday's messages in parallel (batches of 20):

Before probing, filter the enumerated group list against the local blacklist.
This avoids calling `+chat-messages-list` for blacklisted groups.

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

### Step 3 — Present active conversations

Merge non-blacklisted P2P threads and active non-blacklisted groups, then show
the user the confirmation list. Include only an aggregate skipped count:

```text
Skipped by local blacklist: <N>
```

Do not display blacklisted names or IDs in the normal digest flow.

### Step 4 — Wiki cross-reference (enrichment only)

After the user confirms the scan list, cross-reference each active conversation against `$LOCAL_WIKI_ROOT/wiki/entities/customers/*.md` using the `lark_chat` field, person name (for P2P), or fuzzy chat-name match. Attach existing customer/person context for richer analysis. Conversations with no wiki match are flagged as **potential new customer or contact** in the digest.

### Step 5 — User provides additional conversations

The user may add extra group chats (`oc_xxx` or name) or P2P contacts (name or `ou_xxx`) at confirmation time. Resolve names via `+chat-search --keyword` (groups) or `lark-cli contact +search` (P2P). If a user-added conversation is currently blacklisted, say so and ask whether to remove it from the blacklist before including it.

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

Only fetch chats that survived blacklist filtering and user confirmation.

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
