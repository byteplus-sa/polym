# Query Workflow — 3-Source Parallel Search

When a user asks a question, search **3 data sources in parallel** via sub-agents, then aggregate. Detect gaps where SA Wiki is missing and prompt user to compound.

---

## Architecture

```
User question: "<query>"
       │
       ▼
   Decide: 3-source parallel OR direct Wiki only?
       │
       ├── (3-source) Launch 3 sub-agents in ONE message:
       │      ├── Agent-1 → SA Wiki         (Bitable + docs +fetch)
       │      ├── Agent-2 → Lark Messages   (lark-im search)
       │      └── Agent-3 → BytePlus Docs   (WebFetch docs.byteplus.com)
       │
       ▼
Aggregate findings; synthesize answer
       │
       ▼
   Gap check: Wiki missing but other sources have it?
       │       Yes → prompt user: "Add to wiki?"
       │             User agrees → CREATE proposal in write_queue
       │
       └── (Wiki-only) skip parallel; query knowledge_index directly
```

---

## When to use 3-source parallel vs Wiki-only

### Use 3-source parallel (default for most questions)

- "AK/SK 怎么轮换" — could be in wiki, in chat history, in BytePlus docs
- "Seedance 2.0 supports face-ref?" — likely in product docs + chat
- "我们的 SOP 是什么" — could be wiki + chat
- Anything ambiguous about which source has it

### Use Wiki-only (skip parallel)

- "查一下客户 acme-corp 的 PROFILE" — purely wiki content
- "最近的 wiki 更新" — wiki internal
- "wiki 里有哪些 topic 页面" — wiki internal
- "log 表里我提交的 proposal 状态" — wiki/Bitable internal
- Questions about wiki structure, write_queue status, lint reports

---

## Pattern A: 3-source parallel search

**ONE message, 3 Agent calls** (parallel = same message):

### Agent 1 — SA Wiki

```
Agent(
  subagent_type="general-purpose",
  description="Search SA Wiki",
  prompt="""
You are searching the BytePlus SA Wiki (Lark Bitable + Wiki).

Constants:
- BASE_TOKEN=UXPdbPJ3kaheZvs2Nc8lLGCcglh
- KI_TABLE=tblLKeA8N3ipyEQv (knowledge_index)

User question: <QUERY>

Steps:
1. Run keyword search on Knowledge Index Bitable (Title + Keywords + Summary fields)
   lark-cli base +record-search --base-token $BASE_TOKEN --table-id $KI_TABLE \\
     --json '{"filter":{"conjunction":"or","conditions":[
       {"field_name":"Title","operator":"contains","value":["<keyword>"]},
       {"field_name":"Keywords","operator":"contains","value":["<keyword>"]},
       {"field_name":"Summary","operator":"contains","value":["<keyword>"]}
     ]},"page_size":10}' --format json --as user

2. For top 1-3 most relevant rows, fetch the full doc:
   lark-cli docs +fetch --api-version v2 --doc <doc_token> --as user

3. Return: under 300 words, structured as:
   - Found in Wiki: yes/no
   - Most relevant page(s): title + 1-line summary + doc_token
   - Key facts extracted (bullet list)
   - If found nothing useful, say so clearly.
"""
)
```

### Agent 2 — Lark Messages

```
Agent(
  subagent_type="general-purpose",
  description="Search Lark messages",
  prompt="""
Search the user's Lark messages and group chats for relevant context.

User question: <QUERY>

Steps:
1. Use lark-im skill to search recent messages.
   Common command: lark-cli im +messages-search --keyword "<keyword>" --limit 20 --as user
   (Check lark-im SKILL.md for exact syntax)
2. Filter to messages from the last 90 days unless user specifies otherwise.
3. For each relevant hit, capture: chat name, sender, date, message snippet.
4. Return: under 300 words, structured as:
   - Found in chats: yes/no
   - Most relevant snippets (chat name + date + 1-2 sentences each)
   - Group chat URLs / message URLs if available
   - Anonymize sensitive info (PII, customer names if uncertain).
"""
)
```

### Agent 3 — BytePlus Docs

```
Agent(
  subagent_type="general-purpose",
  description="Search BytePlus docs",
  prompt="""
Search the BytePlus official documentation for relevant content.

Entry URL: https://docs.byteplus.com/en/docs
User question: <QUERY>

Steps:
1. WebFetch the docs index/search to locate relevant product / API / guide pages.
   Try search URL or sitemap; fall back to navigating product categories.
2. Identify 1-3 most relevant doc pages.
3. WebFetch each candidate page; extract the section that answers the query.
4. Return: under 300 words, structured as:
   - Found in BytePlus docs: yes/no
   - Most relevant doc page(s): title + URL + 1-line summary
   - Key facts extracted (bullet list, with API names / product feature names exact)
   - Last updated date if visible on the page.
"""
)
```

### Aggregation step (in main agent, after all 3 return)

```
1. Synthesize a unified answer using all 3 sources, citing source per claim:
   - "[SA Wiki] says ..."
   - "[Lark chat in #vision-ai-team on 2026-04-15] says ..."
   - "[BytePlus docs https://docs.byteplus.com/...] says ..."

2. Detect gaps:
   - If Wiki found nothing AND (Messages OR Docs) found something useful
     → trigger COMPOUND PROMPT (see below)

3. Detect contradictions:
   - If sources disagree, surface the conflict to user; don't pick one silently.
```

### Compound prompt (the key feature)

When Wiki is missing but other sources have answers, output to user:

```
📌 知识缺口检测：

   - SA Wiki 里目前没有关于 "<query>" 的 topic 页面
   - 但我在以下源找到了内容：
     • [Lark chat] <chat name> (<date>): "<snippet>"
     • [BytePlus docs]: <URL>

   要不要让我提交一个 CREATE 提议到 write_queue，把这条沉淀进 SA Wiki?
   建议路径: topics/<domain>/<kebab-case-name>
   建议 source_refs: <urls>
```

If user agrees:
- Switch to write-workflow.md → CREATE action
- content_md follows the topic page template (fetch from Wiki: `$META_PAGE_TEMPLATES`)
- Run desensitization (fetch from Wiki: `$META_DESENSITIZATION`)
- Submit proposal to write_queue
- Tell user proposal_id

---

## Pattern B: Wiki-only direct query

For questions clearly about wiki internals (customer profiles, recent updates, proposal status), skip the 3-source dance and go directly to Bitable.

### B.1 — Customer lookup

```bash
lark-cli base +record-search --base-token $BASE_TOKEN --table-id $KI_TABLE \
  --json '{
    "filter": {
      "conjunction": "and",
      "conditions": [
        {"field_name": "Customer", "operator": "is", "value": ["acme-corp"]}
      ]
    },
    "page_size": 50
  }' --format json --as user

# Fetch PROFILE + TIMELINE first (cheapest context); meeting/issue/decision pages by need
lark-cli docs +fetch --api-version v2 --doc <PROFILE_doc_token> --as user
lark-cli docs +fetch --api-version v2 --doc <TIMELINE_doc_token> --as user
```

### B.2 — Domain browse

```bash
lark-cli base +record-list --base-token $BASE_TOKEN --table-id $KI_TABLE \
  --view-id $VIEW_DOM_ACCESS --limit 50 --format json --as user
```

Replace `$VIEW_DOM_ACCESS` with: `$VIEW_DOM_SECURITY`, `$VIEW_DOM_PRODUCT`, `$VIEW_DOM_POC`, `$VIEW_DOM_OPS`, `$VIEW_DOM_ONBOARDING`.

### B.3 — Layer browse

```bash
# All topics
lark-cli base +record-list --base-token $BASE_TOKEN --table-id $KI_TABLE \
  --view-id $VIEW_TOPICS --limit 100 --format json --as user

# All customer pages
lark-cli base +record-list --base-token $BASE_TOKEN --table-id $KI_TABLE \
  --view-id $VIEW_CUSTOMERS --limit 100 --format json --as user
```

### B.4 — What's new

```bash
# All view sorted by Updated desc
lark-cli base +record-list --base-token $BASE_TOKEN --table-id $KI_TABLE \
  --view-id $VIEW_ALL --limit 30 --format json --as user
```

### B.5 — Proposal status

```bash
# Check user's pending proposals
lark-cli base +record-search --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{
    "filter": {
      "conjunction": "and",
      "conditions": [
        {"field_name": "agent_id", "operator": "is", "value": ["sa-wenjie"]},
        {"field_name": "status", "operator": "is", "value": ["pending"]}
      ]
    }
  }' --format json --as user
```

---

## Pagination

`--limit` max 200. If `has_more=true`, paginate with `--page-token`. For >200 results, narrow filter instead.

## Error recovery

| Error | Cause | Fix |
|---|---|---|
| 91403 | No access to Bitable | Confirm user is a member of SA-Wiki space |
| `field_name not found` | Field name typo (case-sensitive) | Re-check field names in SKILL.md §3 |
| Empty results | Filter too narrow OR keyword not in Keywords field | Loosen filter; try synonyms (fetch `$META_GLOSSARY` for canonical terms) |
| `1254015` | Wrong value type for filter | For select use `["option"]`, not bare string |
| Sub-agent timeout | One of 3 parallel agents hung | Don't block — synthesize from the 2 that returned, note the missing source |

## Performance tips

- 3-source parallel adds latency vs single-source; only use when query genuinely spans sources
- Once a topic exists in Wiki, future queries on that topic should resolve from Wiki only (faster)
- Cache results within a session — don't re-query the same thing twice
- Bitable `Summary` field often answers simple questions without `docs +fetch`
