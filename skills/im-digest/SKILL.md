---
name: im-digest
version: 0.3.0
description: "Fetches yesterday's Lark IM messages, organises topics and key content, and saves automatically to the knowledge base. Trigger phrases: 'organize yesterday's messages', 'daily IM digest', 'pull yesterday's group messages', 'im digest'."
metadata:
  requires:
    bins: ["lark-cli"]
---

# im-digest — Yesterday's IM Message Digest

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
- Lark wiki writes delegated to **sa-wiki skill**

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
   - Y: "Where should it be saved? (press Enter for default ~/sa-wiki)" → call `local-wiki-init` → save path to memory
   - N: Skip local write for this run, remember preference

**0.3 Determine Chats to Scan**

1. Read `lark_chat` field from `$LOCAL_WIKI_ROOT/wiki/entities/customers/*.md`
2. Supplement using `lark-cli im +chat-search --keyword <name>` for unrecorded chats
3. User may append chat names / chat_ids

Display the list of chats to be scanned and wait for confirmation.

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

**Execute automatically using sa-wiki skill §5 WRITE workflow. Do not mention "dual-write" to the user.**

Read `~/.claude/skills/sa-wiki/SKILL.md` §5 and follow its process:
- APPEND TIMELINE (for each customer with content)
- CREATE/APPEND feedback / error-code pages (Feature Asks, Technical Issues)
- Risk signals → APPEND TIMELINE with risk tag
- Auto-apply desensitization before writing (`META_DESENSITIZATION`, managed by sa-wiki)

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

- Do not `docs +update` wiki pages directly — all writes go through sa-wiki write_queue
- Desensitization is handled by sa-wiki (`META_DESENSITIZATION`)
- Raw snapshots are read-only
- Only process group chats, not P2P messages

## Reference Documents

- [`references/fetch-workflow.md`](references/fetch-workflow.md)
- [`references/digest-schema.md`](references/digest-schema.md)
- [`core/local-wiki-ux.md`](../../core/local-wiki-ux.md)
