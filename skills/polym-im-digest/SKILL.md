---
name: polym-im-digest
version: 0.7.2
description: "Fetches yesterday's Lark IM messages, organises topics and key content, materialises a Feishu digest doc for the day, and saves automatically to the knowledge base. Trigger phrases: 'organize yesterday's messages', 'daily IM digest', 'pull yesterday's group messages', 'im digest'."
metadata:
  requires:
    bins: ["lark-cli"]
---

# polym-im-digest — Yesterday's IM Message Digest

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
- "把这个群加入 IM digest 黑名单"
- "以后不要拉某人的 IM digest"
- "列出 / 移除 IM digest 黑名单"
- "每天自动跑 IM digest"
- "帮我创建每天跑 IM digest 的 Codex routine"

## Dependencies

- `lark-cli` (`im` module for fetch; `docs` + `drive` modules for the Feishu doc output)
- Local wiki (path auto-resolved, see Phase 0)
- Lark wiki writes delegated to **polym-sa-wiki skill**
- Local blacklist file (see Phase 0.3)
- Optional product context map (see `references/product-context.md`)
- Optional Codex routine setup guidance (see `references/codex-routine.md`)
- Feishu doc visual style guide (see `references/doc-visual-style.md`)

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
   - Y: "Where should it be saved? (press Enter for default ~/sa-wiki)" → call `polym-local-wiki-init` → save path to memory
   - N: Skip local write for this run, remember preference

**0.3 Local Blacklist Resolution and Maintenance**

Resolve the IM digest blacklist before discovering active conversations:

1. If `LOCAL_WIKI_ROOT` is valid, use:
   `$LOCAL_WIKI_ROOT/config/polym-im-digest-blacklist.json`
2. Otherwise use:
   `~/.config/polym/im-digest/blacklist.json`
3. If the file does not exist, treat the blacklist as empty. Do not ask during
   normal digest runs.

Blacklist entries are long-lived local preferences. They are never written to
the Lark wiki or Feishu docs.

Schema:

```json
{
  "version": 1,
  "groups": [
    {
      "chat_id": "oc_xxx",
      "name": "optional display name",
      "reason": "optional",
      "created_at": "2026-05-26T10:00:00+08:00"
    }
  ],
  "p2p": [
    {
      "chat_id": "oc_xxx",
      "open_id": "ou_xxx",
      "name": "optional display name",
      "reason": "optional",
      "created_at": "2026-05-26T10:00:00+08:00"
    }
  ]
}
```

Management requests:

| User intent | Action |
|---|---|
| "Add this group / `<oc_xxx>` / `<name>` to blacklist" | Resolve to `chat_id` when needed, append to `groups`, de-dupe by `chat_id` |
| "Add this person / `<ou_xxx>` / `<name>` to blacklist" | Resolve to `open_id` and/or P2P `chat_id` when possible, append to `p2p`, de-dupe by `open_id` then `chat_id` |
| "Remove ..." | Remove matching `chat_id`, `open_id`, or exact name |
| "List blacklist" | Show local blacklist path and entries |

During digest execution:

- Group blacklist is applied before the activity probe. Do not call
  `+chat-messages-list` for blacklisted group `chat_id`s or exact group-name
  matches.
- P2P blacklist is applied immediately after the global P2P discovery query.
  Blacklisted P2P chats are removed before the confirmation list, Phase 1
  fetch, analysis, raw snapshots, Feishu doc, and knowledge-base writes.
- Do not print blacklisted chats in the normal active conversation list. Report
  only aggregate counts such as `Skipped by local blacklist: <N>`.

**0.4 Discover Active Conversations from Lark (message-first)**

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
lark-cli im chats list \
  --as user \
  --page-all --page-limit 5 \
  --params '{"page_size":100,"sort_type":"ByActiveTimeDesc"}' \
  --format json
# page-limit 5 caps discovery at 500 groups.
#
# Do not use `lark-cli im +chat-search` for full enumeration: current
# lark-cli requires --query or --member-ids for +chat-search, so an empty
# search cannot list every joined group.
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
Also skip blacklisted groups before probing.

**Step 3 — Categorise and show the active-conversation list to the user**

Merge P2P threads (Step 1) and active groups (Step 2), remove blacklisted
conversations, then display:

```
Active conversations on <YESTERDAY> — <N> total

📨 P2P / direct messages (<n>):
  [chat_id] Person Name — <k> messages

👥 External / customer group chats (<n>):
  [oc_xxx] Chat Name — <k> messages

🏢 Internal / team / notification group chats (<n>):
  [oc_xxx] Chat Name — <k> messages

🔒 No-access (<n>): <names>

Skipped by local blacklist: <n>
```

Wait for user confirmation or exclusion requests before proceeding to Phase 1.

**Step 4 — Wiki cross-reference (enrichment only)**

After the user confirms the scan list, look up each active conversation against `$LOCAL_WIKI_ROOT/wiki/entities/customers/*.md` (matching on `lark_chat` field, person name, or chat name). Attach existing customer/person context for richer Phase 2 analysis. Conversations with no wiki match are flagged as **potential new customer or contact** in the digest.

**Step 5 — Product context enrichment**

Apply `references/product-context.md` before analysis:

- Tag every conversation and extracted signal with product line,
  offering/model, and capability/modality.
- Use three fields: product line, offering/model, and capability/modality.
- `ModelArk / MaaS` always sorts before public cloud, infra, ops, and
  miscellaneous content.
- Do not use `AIGC Video / Image` as a product line. Treat it as capability or
  modality for Seedance / Seedream workflows.
- Recognise Seedance, Seedream, Ark, ModelArk, Doubao, xLLM, Viking, ArkClaw,
  AgentKit, OpenAI-compatible API, quota, endpoint, reasoning, TTFT, TPM/RPM,
  and embedding as MaaS / model-platform signals unless the conversation makes a
  different product ownership explicit.
- If a known product such as Seedance has active messages but no corresponding
  digest item, run a second pass over raw messages for that product before
  rendering.

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

### Phase 2 — Priority-First Analysis

See [`references/digest-schema.md`](references/digest-schema.md):

1. Extract the 12 signal dimensions.
2. Classify each signal by product line, offering/model, and capability using
   `references/product-context.md`.
3. Assign priority `P0` / `P1` / `P2` / `P3`.
4. Extract owner, deadline, source channel, background, status, next step, and
   evidence timestamp for every priority item.
5. Fold duplicate descriptions into one canonical issue. Do not describe the
   same OKX/Snapdeal/etc. issue once in a top table and again as a separate
   full section unless the lower section only provides compact evidence.
6. Run coverage checks before rendering:
   - Executive summary exists.
   - ModelArk / MaaS signals are sorted first.
   - Every `P0`/`P1` has owner/deadline fields, even if `TBD`.
   - Known active products such as Seedance are represented when raw messages
     contain matching terms.
   - Channel/background is present for every highlight and issue.

---

### Phase 3 — Output Digest

Render the structured summary following `references/digest-schema.md` § Output
Format and `references/doc-visual-style.md`. The digest must start with:

1. title and run metadata
2. `## Executive Summary`
3. `### Priority Queue`
4. `### Owner / Deadline Gaps`

Then continue with product drill-down, cross-chat patterns, risks, pipeline, and
chat appendix. Show a markdown copy in the terminal **and** persist both a
terminal-friendly Markdown fallback and the Feishu visual XML source:

```
DIGEST_MD="${TMPDIR:-/tmp}/polym-im-digest-${YESTERDAY}.md"
DIGEST_XML="${TMPDIR:-/tmp}/polym-im-digest-${YESTERDAY}.visual.xml"
```

The Markdown file is for terminal review and fallback only. The XML file is the
source of truth Phase 4 hands to `lark-cli docs +create`. The XML renderer MUST
use Feishu visual blocks from `references/doc-visual-style.md` for metric cards,
callouts, colored priority tables, real tables, checkboxes, bookmarks, and
section dividers. Do not rely on Markdown pipe tables for Feishu docs because
they may render as plain text.

Content parity is mandatory:

- The XML visual doc must contain every section present in the Markdown digest:
  Executive Summary, Priority Queue, Owner / Deadline Gaps, Highlights, Product
  Area Drill-Down, Cross-Chat Patterns, Risks, Business / Pipeline Updates, and
  Chat Appendix.
- Visual rendering may reorder blocks for readability, but it must not drop
  P2/P3 items, low-signal summaries, risks, pipeline rows, or appendix evidence.
- Before Phase 4, compare the Markdown and XML section outlines. If any Markdown
  section is missing from XML, fix XML before creating or updating the Feishu
  doc.

Proceed directly to Phase 4 after rendering — do not ask the user.

---

### Phase 4 — Create Feishu Doc

Materialise the digest as a standalone Feishu document so the user has a real
artefact to open / share, not just terminal output.

**4.1 Ask the user where to put it (once per run)**

> "Where should the Feishu doc go?
>   - Press Enter for the root of your personal Feishu drive (default)
>   - Paste a folder URL like `https://bytedance.larkoffice.com/drive/folder/fldcn...`
>   - Or reply `new <name>` to create a new folder for it"

Parse the reply:

| Reply | Action |
|---|---|
| empty / Enter | `FOLDER_TOKEN=""` (personal drive root) |
| folder URL | extract token from `/drive/folder/<token>` |
| `new <name>` | `lark-cli drive +folder-create --name "<name>" --parent-token "" --as user --format json` → capture `data.token` |

**4.2 Create the doc**

Default visual XML path:

```bash
cd "$(dirname "$DIGEST_XML")"
lark-cli docs +create --api-version v2 \
  --title "IM Digest · ${YESTERDAY}" \
  --content @"$(basename "$DIGEST_XML")" \
  --doc-format xml \
  --folder-token "$FOLDER_TOKEN" \
  --as user
# → capture data.document.document_id  → DOC_TOKEN
# → capture data.url (if returned) or build:
#   DOC_URL="https://bytedance.larkoffice.com/docx/${DOC_TOKEN}"
```

Current `lark-cli` requires `@file` paths to be relative to the current working
directory and may reject `--format` on this shortcut. Change into the digest
directory before calling `docs +create`, and parse the JSON emitted on stdout.

Fallback compatible Markdown path if XML creation fails:

```bash
cd "$(dirname "$DIGEST_MD")"
lark-cli docs +create --api-version v2 \
  --title "IM Digest · ${YESTERDAY}" \
  --content @"$(basename "$DIGEST_MD")" \
  --doc-format markdown \
  --folder-token "$FOLDER_TOKEN" \
  --as user
```

Use the Markdown fallback only after the XML create command fails. Report the
fallback in Phase 7 if it was used.

**4.3 Failure handling**

- `lark-cli` not authenticated / scope missing → print one-line warning with the
  exact `lark-cli auth login` hint, keep `DOC_URL=""`, and continue. Do not
  block the rest of the flow — local wiki and write_queue writes are still
  valuable on their own.
- Folder token invalid → retry once with `FOLDER_TOKEN=""`; if still failing,
  same graceful fallback as above.

The doc URL is reported back in Phase 7. No state file is persisted — the user
is asked again on the next interactive run.

---

### Phase 5 — Write to Local Wiki (Silent)

**Only execute when LOCAL_WIKI_ROOT is valid. Do not notify the user.**

Follow `$LOCAL_WIKI_ROOT/SCHEMA.md`: raw is read-only, bidirectional relationships, absolute dates, no todos.

1. Update `wiki/entities/customers/<slug>.md` (Recent interactions, Products in play, Open feedback)
2. Create `wiki/sources/chat-<slug>-<YESTERDAY>.md`
3. Update `wiki/index.md` + append to `wiki/log.md`

---

### Phase 6 — Write to Lark Wiki

**Execute automatically using polym-sa-wiki skill §5 WRITE workflow. Do not mention "dual-write" to the user.**

Read `~/.claude/skills/polym-sa-wiki/SKILL.md` §5 and follow its process:
- APPEND TIMELINE (for each customer with content)
- CREATE/APPEND feedback / error-code pages (Feature Asks, Technical Issues)
- Risk signals → APPEND TIMELINE with risk tag
- Auto-apply desensitization before writing (`META_DESENSITIZATION`, managed by polym-sa-wiki)

---

### Phase 7 — Final Report

```
✅  Yesterday's (<YESTERDAY>) IM digest complete

Scanned <N> chats · <M> valid messages
Skipped by local blacklist: <B> chats

📄 Feishu doc: <DOC_URL>
   (or "(skipped — see Phase 4 warning)" if creation failed)

Summary:
  Customer feedback: <N>  Feature asks: <N>
  P0/P1 items: <N>  Owner/deadline gaps: <N>
  ModelArk / MaaS items: <N>
  Competitive signals: <N> (customers: <A>, <B>)
  ⚠️ Risk signals: <N> (recommended proactive follow-up: <customer name>)

Saved <K> entries to knowledge base (<proposal_ids>)
```

Risk-signal customers are highlighted for SA prioritization.

---

## Security Rules

- Do not `docs +update` wiki pages directly — all writes go through polym-sa-wiki write_queue
- Desensitization is handled by polym-sa-wiki (`META_DESENSITIZATION`)
- Raw snapshots are read-only
- Process both group chats and P2P messages; treat P2P content with higher sensitivity (colleague discussions may be more candid)
- Never write blacklist contents to Feishu docs, Lark wiki, raw snapshots, or
  digest output beyond aggregate skipped counts.

## Reference Documents

- [`references/fetch-workflow.md`](references/fetch-workflow.md)
- [`references/digest-schema.md`](references/digest-schema.md)
- [`references/product-context.md`](references/product-context.md)
- [`references/doc-visual-style.md`](references/doc-visual-style.md)
- [`references/codex-routine.md`](references/codex-routine.md)
- [`references/blacklist.md`](references/blacklist.md)
- [`core/local-wiki-ux.md`](../../core/local-wiki-ux.md)
