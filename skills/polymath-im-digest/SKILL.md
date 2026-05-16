---
name: polymath-im-digest
version: 0.4.0
description: "Fetches yesterday's Lark IM messages, organises topics and key content, and saves automatically to the knowledge base. Trigger phrases: 'organize yesterday's messages', 'daily IM digest', 'pull yesterday's group messages', 'im digest'."
metadata:
  requires:
    bins: ["lark-cli"]
---

# polymath-im-digest — Yesterday's IM Message Digest

Compiles Lark group chat information into structured knowledge daily and saves it automatically.

## Trigger Scenarios

- "Organize yesterday's messages"
- "Pull yesterday's group messages"
- "daily IM digest"
- "im digest"
- "Help me summarize yesterday's IM"
- "Organize yesterday's chat history into the knowledge base"
- "整理昨天的消息"
- "拉一下昨天的群消息"
- "帮我总结一下昨天的 IM"

## Dependencies

- `lark-cli` (im module)
- Local wiki (path auto-resolved, see Phase 0)
- Lark wiki writes delegated to **polymath-sa-wiki skill**

---

## Full Execution Flow

### Phase 0 — Preparation

**0.1 Calculate Time Range**

```bash
# macOS
YESTERDAY=$(date -v-1d +%Y-%m-%d)
START_TIME="${YESTERDAY}T00:00:00+08:00"
END_TIME="${YESTERDAY}T23:59:59+08:00"

# Linux
YESTERDAY=$(date -d yesterday +%Y-%m-%d)
```

**0.2 Local Wiki Resolution (per `core/local-wiki-ux.md` standard)**

1. Check `LOCAL_WIKI_ROOT` environment variable
2. Check Claude memory system for a `local-wiki-root` memory entry
3. Auto-detect common paths: `~/sa-wiki`, `~/wiki`, `~/LLM-Wiki`
4. If none found → ask once: "No local wiki found. Would you like to create one? [Y/n]"
   - Y: "Where should it be saved? (press Enter for default ~/sa-wiki)" → call `polymath-local-wiki-init` → save path to memory
   - N: Skip local write for this run, remember preference

**0.3 Discover Active Conversations from Lark (message-first)**

> **Principle: messages are the ground truth. The local wiki is used only for context enrichment afterward — never as the primary source for discovering which conversations to scan.**

**Steps 1 & 2 — Run in parallel**

Fire both branches simultaneously; merge results before Step 3.

**Step 1 — Collect all P2P messages from yesterday (one query)**

```bash
lark-cli im +messages-search \
  --chat-type p2p \
  --start "$START_TIME" --end "$END_TIME" \
  --exclude-sender-type bot \
  --page-all \
  --format json \
  --as user
```

Returns every P2P message (sent or received) in a single paginated query — no need to enumerate contacts first. Group results by `chat_id` to reconstruct per-conversation threads.

**Step 2 — Enumerate ALL joined group chats and probe for activity**

This covers every group the user is in — including new customer groups not yet in the local wiki.

```bash
# Enumerate ALL joined groups, newest-activity first
lark-cli im +chat-search \
  --sort-by update_time_desc \
  --page-size 100 \
  --format json \
  --as user
# Repeat with --page-token until has_more=false (cap at 500 groups)
```

For every group returned, batch-probe for yesterday's messages in parallel (batches of 20):

```bash
lark-cli im +chat-messages-list \
  --chat-id <oc_xxx> \
  --start "$START_TIME" --end "$END_TIME" \
  --sort asc --page-size 1 \
  --format json --as user
# page-size 1 for probe; re-fetch with page-size 50 in Phase 1 if active
```

Skip silently: 0 messages, access error (`99991400` / `403`).

**Step 3 — Categorise and show the active-conversation list to the user**

Merge P2P threads (Step 1) and active groups (Step 2), then display:

```
Active conversations on <YESTERDAY> — <N> total

📨 P2P / direct messages (<n>):
  [chat_id] Person Name — <k> messages

👥 External / customer group chats (<n>):
  [oc_xxx] Chat Name — <k> messages

🏢 Internal / team / notification group chats (<n>):
  [oc_xxx] Chat Name — <k> messages

🔒 No-access (<n>): <names>
```

Wait for user confirmation or exclusion requests before proceeding to Phase 1.

**Step 4 — Wiki cross-reference (enrichment only)**

After the user confirms the scan list, look up each active conversation against `$LOCAL_WIKI_ROOT/wiki/entities/customers/*.md` (matching on `lark_chat` field, person name, or chat name). Attach existing customer/person context for richer Phase 2 analysis. Conversations with no wiki match are flagged as **potential new customer or contact** in the digest.

---

### Phase 1 — Fetch Messages

```bash
lark-cli im +chat-messages-list \
  --chat-id <oc_xxx> \
  --start "$START_TIME" --end "$END_TIME" \
  --sort asc --page-size 50 --format json --as user
```

Paginate when `has_more=true` (limit: 10 pages / 500 messages).

Write raw messages to: `$LOCAL_WIKI_ROOT/raw/chat-<slug>-<YESTERDAY>.md` (if local wiki exists)

---

### Phase 2 — 12-Dimension Analysis

See [`references/digest-schema.md`](references/digest-schema.md):

| # | Dimension |
|---|---|
| 1 | Key Points |
| 2 | Customer Feedback — Positive |
| 3 | Customer Feedback — Negative |
| 4 | Feature Asks |
| 5 | Technical Issues & Errors |
| 6 | Business Progress |
| 7 | Competitive Intelligence |
| 8 | ⚠️ Risk Signals |
| 9 | Usage & Quota |
| 10 | Personnel & Org Changes |
| 11 | Product Misunderstandings |
| 12 | Decisions & Pending Items |

---

### Phase 3 — Output Digest

Output the structured summary in the terminal (format defined in `references/digest-schema.md` § Output Format).

**Proceed directly to the write phase after output — do not ask the user.**

---

### Phase 4 — Write to Local Wiki (Silent)

**Only execute when LOCAL_WIKI_ROOT is valid. Do not notify the user.**

Follow `$LOCAL_WIKI_ROOT/SCHEMA.md`: raw is read-only, bidirectional relationships, absolute dates, no todos.

1. Update `wiki/entities/customers/<slug>.md` (Recent interactions, Products in play, Open feedback)
2. Create `wiki/sources/chat-<slug>-<YESTERDAY>.md`
3. Update `wiki/index.md` + append to `wiki/log.md`

---

### Phase 5 — Write to Lark Wiki

**Execute automatically using polymath-sa-wiki skill §5 WRITE workflow. Do not mention "dual-write" to the user.**

Read `~/.claude/skills/polymath-sa-wiki/SKILL.md` §5 and follow its process:
- APPEND TIMELINE (for each customer with content)
- CREATE/APPEND feedback / error-code pages (Feature Asks, Technical Issues)
- Risk signals → APPEND TIMELINE with risk tag
- Auto-apply desensitization before writing (`META_DESENSITIZATION`, managed by polymath-sa-wiki)

---

### Phase 6 — Final Report

```
✅  Yesterday's (<YESTERDAY>) IM digest complete

Scanned <N> chats · <M> valid messages

Summary:
  Customer feedback: <N>  Feature asks: <N>
  Competitive signals: <N> (customers: <A>, <B>)
  ⚠️ Risk signals: <N> (recommended proactive follow-up: <customer name>)

Saved <K> entries to knowledge base (<proposal_ids>)
```

Risk-signal customers are highlighted for SA prioritization.

---

## Security Rules

- Do not `docs +update` wiki pages directly — all writes go through polymath-sa-wiki write_queue
- Desensitization is handled by polymath-sa-wiki (`META_DESENSITIZATION`)
- Raw snapshots are read-only
- Process both group chats and P2P messages; treat P2P content with higher sensitivity (colleague discussions may be more candid)

## Reference Documents

- [`references/fetch-workflow.md`](references/fetch-workflow.md)
- [`references/digest-schema.md`](references/digest-schema.md)
- [`core/local-wiki-ux.md`](../../core/local-wiki-ux.md)
