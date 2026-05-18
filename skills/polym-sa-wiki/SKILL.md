---
name: polym-sa-wiki
version: 0.3.0
description: "BytePlus SA Team knowledge base — read and write. Use when asking about SA knowledge, customer profiles, meeting notes, archiving information, checking customer progress, adding topic pages, or ingesting handbook chapters. READ path: Bitable knowledge_index search + full-text docs fetch. WRITE path: mandatory write_queue (agents never write wiki pages directly). Multi-agent concurrency-safe. Operational tutorials (containing URL + step-by-step instructions) trigger an optional Chrome MCP browser demo offer — see references/browser-demo.md."
metadata:
  requires:
    bins: ["lark-cli"]
---

# SA Wiki — Knowledge Base Skill

> **Prerequisites:** Read [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md) (auth, `--as user` default) and [`../lark-base/SKILL.md`](../lark-base/SKILL.md) (Bitable operations).

Shared SA Team knowledge base, concurrency-safe for multiple agents. **READ queries Bitable directly + full-text fetch; WRITE always goes through the write_queue** — agents never write wiki pages directly.

## 1. When to Use This Skill

### 1.1 Trigger Scenarios (any of these)

- "check SA wiki / our knowledge base / this customer's situation"
- "what do we know about customer X", "X's recent progress"
- "file this meeting note into the wiki"
- "create a new topic page", "add a SOP / FAQ entry"
- "organize this chat content into the knowledge base"
- "add a handbook chapter to sources"
- "look up SA knowledge about access / security / product"
- "how to rotate AK/SK", "Babi SSO known issues", and other specific business questions

### 1.2 When NOT to Use

- User just wants to read a specific Lark document (→ `lark-doc`)
- User provides a Bitable URL directly (→ `lark-base`)
- User is sending a message in a group chat (→ `lark-im`)
- User is asking about developer console / scope management (→ `lark-shared`)

## 2. Architecture (read this first)

### 2.1 Three-Layer Karpathy Architecture

```
sources/      Layer 1  Raw materials (immutable: handbook / meeting raw / chat exports / policy docs)
   ↓ ingest
topics/  +  customers/   Layer 2  Distilled knowledge + customer profiles (high-frequency agent reads)
   ↓ query
Answer → compound new insights → write_queue → new page (compound)
                                ↓
                       LOG table append one row
```

**Key invariants:**
- `sources/` never modified, only ADDED
- `write_queue` is the only write entry point — cannot be bypassed
- Every write is serially committed by the coordinator + writes a log entry

### 2.2 Physical Structure

```
SA-Wiki (space_id=7636607758988626894)
├── 00 · README              schema / multi-agent protocol
├── 01 · INDEX               docx main navigation (points to Bitable views)
├── 02 · DATA                Bitable: 3 tables + multiple views
├── 03 · sources/            handbook / meetings-raw / chat-archives / policy-docs
├── 04 · topics/             access / security / products / poc-playbook / onboarding / operations
├── 05 · customers/          one subtree per customer: PROFILE / TIMELINE / meetings / poc / issues / decisions
└── 06 · meta/               desensitization / glossary / lint / retention / page-templates
```

## 3. Constants (copy-paste ready)

```bash
# Wiki
WIKI_SPACE_ID="7636607758988626894"
WIKI_README_NODE="B5UewSWRRiKtFJkxBxlcz8yFnn8"
WIKI_INDEX_NODE="MatBwo7VKiso8hkm7hqc0S5dnjg"
WIKI_SOURCES_NODE="OSLgwQk5hicApHkwD9XcQuJHneb"
WIKI_TOPICS_NODE="FRFxwalKRiZEpnkANdJcGEvGnpf"
WIKI_CUSTOMERS_NODE="SaGKw2s5tixMHkkQGEGcE1oAnKf"
WIKI_META_NODE="CPDNw6y2LiufkskbSfBcQwnzn7b"

# Bitable
BASE_TOKEN="UXPdbPJ3kaheZvs2Nc8lLGCcglh"
KI_TABLE="tblLKeA8N3ipyEQv"     # knowledge_index
WQ_TABLE="tblTR65mRdvE74Lu"     # write_queue
LOG_TABLE="tblcMspJB6BvWcoX"    # log

# Wiki meta pages (live source of truth — fetch these before writing)
META_PAGE_TEMPLATES="AK56dDr5ooxg7WxWQI2lT8D9gfg"
META_DESENSITIZATION="PAkrdxuhFocKKgxH8ABlGLOng3b"
META_GLOSSARY="K5r6d0ww6oCr9bxGWH7lG8AEgLe"
META_LINT_CHECKLIST="SjLQdZPu2o9yfAxIleDljr3ZgVf"
META_RETENTION_RULES="RTxYdKqnxodWvcxqDjRl4bqdgpf"

# knowledge_index views (Layer / Domain / All)
VIEW_ALL="vewHanmc0S"           # All — sorted by Updated
VIEW_TOPICS="vewKdnHaJf"
VIEW_CUSTOMERS="vewFNHm7XG"
VIEW_SOURCES="vew0Iqi4ro"
VIEW_META="vewUf8Zhfm"
VIEW_DOM_ACCESS="vewiU5R87h"
VIEW_DOM_SECURITY="vewLyVIqW5"
VIEW_DOM_PRODUCT="vewqXXrbwB"
VIEW_DOM_POC="vewEswsVw8"
VIEW_DOM_OPS="vew37R6Xqz"
VIEW_DOM_ONBOARDING="vewCnhCxk3"

# write_queue views
VIEW_WQ_PENDING="vewbiHHbfb"
VIEW_WQ_REJECTED="vew4BsGegp"
VIEW_WQ_COMMITS="vew54q677F"

# log views
VIEW_LOG_RECENT="vewv9zXG8S"
VIEW_LOG_BY_SA="vewIEpU2yt"
```

## 4. READ Workflow (3-source parallel + gap feedback)

**Core principle**: knowledge queries do not only search SA Wiki — run **3 data sources in parallel** and aggregate results. If SA Wiki has nothing but another source does, immediately tell the user "want to add this to the wiki?" — this is the entry point for the compound accumulation mechanism.

### 3 Data Sources

| Source | Content | Tool |
|---|---|---|
| 1️⃣ **SA Wiki** (our knowledge base) | Distilled topics / customers / sources | `lark-cli base +record-search` + `docs +fetch` |
| 2️⃣ **Lark Messages** (group chat / P2P history) | Live discussions, unsettled temporary conclusions | `lark-cli im +messages-search` |
| 3️⃣ **BytePlus Docs** (official docs) | Product APIs, SDKs, latest releases | WebFetch `https://docs.byteplus.com/en/docs` |

### Implementation: 3 Parallel Sub-Agents

**Required: issue all 3 Agent calls in the same message** (not sequential), each handling one source:

```python
# Agent 1: SA Wiki
Agent(subagent_type="general-purpose",
      description="Search SA Wiki",
      prompt="Use polym-sa-wiki skill query-workflow.md. Search SA Wiki for: '<query>'. ...")

# Agent 2: Lark Messages
Agent(subagent_type="general-purpose",
      description="Search Lark messages",
      prompt="Use lark-im skill. Search the user's recent messages and group chats for: '<query>'. ...")

# Agent 3: BytePlus Docs
Agent(subagent_type="general-purpose",
      description="Search BytePlus docs",
      prompt="WebFetch https://docs.byteplus.com/en/docs and search for: '<query>'. ...")
```

Detailed sub-agent prompt templates: [`references/query-workflow.md`](references/query-workflow.md).

### Aggregation + Gap Feedback

After all 3 sources return:

1. **Synthesize answer**: combine all 3 sources into a final response
2. **Detect gaps**: if (2) or (3) has content but (1) Wiki does not → proactively tell the user:

   > "I found the answer to this in [Lark group chat / BytePlus official docs], but there is no related page in SA Wiki. Would you like me to submit a CREATE proposal to write_queue to archive this into the wiki?"

3. User agrees → follow [WRITE workflow](§5) to create a topic page, with source_refs pointing to the found chat URL / doc URL

### Direct Wiki Query (when the question is clearly wiki-internal)

Some scenarios clearly only need wiki (e.g., "recent wiki updates", "customer X's PROFILE") — skip the 3-source parallel:

```bash
# A. Keyword search
lark-cli base +record-search --base-token $BASE_TOKEN --table-id $KI_TABLE \
  --json '{"keyword":"AK/SK","page_size":20}' --format json --as user

# B. Fetch by view
lark-cli base +record-list --base-token $BASE_TOKEN --table-id $KI_TABLE \
  --view-id $VIEW_DOM_ACCESS --limit 50 --format json --as user

# C. Fetch full text after getting doc_token
lark-cli docs +fetch --api-version v2 --doc <doc_token> --as user
```

> ⚠️ Bitable commands output markdown tables by default. When the agent needs programmatic parsing, **always add `--format json`**.

**Agent decision tree:**
1. "look up a customer"? → `record-search` with customer name, or `record-list` with `VIEW_CUSTOMERS` filter
2. "look up a domain"? → `record-list` with the corresponding `VIEW_DOM_*`
3. "what was updated recently"? → `record-list` with `VIEW_ALL` (sorted by Updated desc)
4. vague question? → `record-search` keyword search, then fetch full text of hits

### Demo Offer (optional read-path tail)

After answering the user's question, evaluate whether the fetched content looks like an **operational tutorial** (URL + step-by-step + action verbs). If yes, append a single offer line to the reply:

> 📺 This page contains operational steps. Want me to walk you through it in the browser? (1) browser demo  (2) read-only (already given above)  (3) re-search

If user picks **(1)** → follow [`references/browser-demo.md`](references/browser-demo.md) for Chrome MCP execution (rhythm rules, visual highlights, GIF recording, sensitive-action guards).
If user picks **(2)** or content is **not demonstrable** → skip silently.

Heuristic scoring + complete demo runbook lives in [`references/browser-demo.md`](references/browser-demo.md). This is purely a read-side render enhancement — wiki schema is unchanged.

## 5. WRITE Workflow (mandatory write_queue)

Full details: [`references/write-workflow.md`](references/write-workflow.md). Short version:

```bash
# Step 1: Fetch latest desensitization rules (wiki is source of truth — don't rely on memory)
lark-cli docs +fetch --api-version v2 --doc $META_DESENSITIZATION --as user
# Step 2: Fetch the relevant page template
lark-cli docs +fetch --api-version v2 --doc $META_PAGE_TEMPLATES --as user
# Step 3: Submit write_queue proposal
lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{
    "fields": {
      "SA": "<your Lark display name, e.g. 王文杰>",
      "action": "CREATE",
      "target_path": "topics/access/ak-sk-lifecycle",
      "content_md": "<full markdown body>",
      "source_refs": "<source URLs>",
      "status": "pending"
    }
  }' --as user

# ⚠️ Field name is `SA` (the real-person owner), NOT `agent_id`. Value is the Lark display
# name of the SA who owns this proposal (e.g. 王文杰). The agent / model running on the
# SA's behalf is recorded separately in the log table's agent_id column at commit time.

# Step 4: Get proposal_id (P-XXXXX), tell user "queued, waiting for coordinator commit"
# Step 5: After user/coordinator processes it, status changes to committed / rejected
```

**4 action types:**
- `CREATE` — new page (target_path must follow naming conventions; leave target_doc_token empty)
- `APPEND` — append to an existing page (target_doc_token required)
- `REPLACE` — overwrite entire page (target_doc_token required; use sparingly)
- `LINT` — request a cleanup task (free-form note; coordinator handles)

## 6. Naming Conventions (strictly enforced)

| Page type | target_path format |
|---|---|
| Topic | `topics/<domain>/<kebab-case-name>` |
| Customer profile | `customers/<customer-name>/PROFILE` |
| Customer timeline | `customers/<customer-name>/TIMELINE` |
| Meeting note | `customers/<customer-name>/meetings/<YYYY-MM-DD>-<slug>` |
| Customer issue | `customers/<customer-name>/issues/<YYYY-MM>-<slug>` |
| Customer decision | `customers/<customer-name>/decisions/<YYYY-MM-DD>-<slug>` |
| Source | `sources/<subfolder>/<descriptive-name>` |

**Customer name**: default is the real name (e.g., `acme-corp`); if SA requests anonymization, use the SA-provided alias (e.g., `opn**art`). Mapping is not stored in wiki.

## 7. Multi-Agent Concurrency Safety

- **Reads**: fully concurrent, no locks
- **Writes**: forced serial, all go through `write_queue`
- **Dedup**: proposals with the same `target_path` in pending state are marked `superseded` by the coordinator
- **Conflict**: REPLACE operations checked by coordinator against target's `last_committed_at`; conflicts auto-rejected
- **Audit**: every commit writes a row to the `log` table (includes `SA` real-person owner + `agent_id` of the executing agent + `proposal_id`)

## 8. Before Writing: Desensitization

**Wiki is the single source of truth** — desensitization rules are maintained only in the wiki, not copied into skills:

```bash
lark-cli docs +fetch --api-version v2 --doc $META_DESENSITIZATION --as user
```

**Any CREATE/APPEND/REPLACE proposal must pass this checklist first**, or the coordinator will directly reject it.

Quick reference (detailed rules in wiki):
- ❌ Actual AK/SK / tokens / passwords
- ❌ Customer PII (name, phone, email, ID number, bank account)
- ❌ Individual SIP amounts, performance scores
- ❌ L4-classified document full text
- ❌ Real customer names in topics/ pages (anonymize as [Customer A])

## 9. Compound Principle

Karpathy core: **let query outputs settle back into the wiki**.

If an agent during querying:
- Discovers a new generalizable insight (not belonging to any existing topic) → propose creating a new topic page
- Discovers a customer issue linked to an existing topic → bidirectional link (add links in both customers/ and topics/)
- Discovers contradictions or gaps in existing pages → submit a LINT proposal

Don't let valuable answers disappear in chat.

## 10. References

**Skill local files** (CLI workflows, stable):

| File | Content |
|---|---|
| [query-workflow.md](references/query-workflow.md) | Complete READ decision tree + command templates |
| [write-workflow.md](references/write-workflow.md) | Complete steps for all 4 actions + error handling |
| [examples.md](references/examples.md) | End-to-end examples: customer lookup, meeting archive, new topic, bug report |

**Wiki sources of truth** (business rules, change over time — fetch latest before every write):

| Purpose | doc_token constant | fetch command |
|---|---|---|
| Page templates (7 types) | `$META_PAGE_TEMPLATES` | `lark-cli docs +fetch --api-version v2 --doc $META_PAGE_TEMPLATES --as user` |
| Desensitization decision matrix | `$META_DESENSITIZATION` | `... --doc $META_DESENSITIZATION ...` |
| Controlled vocabulary | `$META_GLOSSARY` | `... --doc $META_GLOSSARY ...` |
| Periodic cleanup checklist | `$META_LINT_CHECKLIST` | `... --doc $META_LINT_CHECKLIST ...` |
| Content retention rules | `$META_RETENTION_RULES` | `... --doc $META_RETENTION_RULES ...` |

> ⚠️ Skill **does not cache** wiki content. Fetch before every write to avoid stale data.

## 11. Safety Rules

- Default `--as user`; confirm user intent before any write operation
- Never use `docs +update` to modify wiki pages directly (unless user explicitly requests bypassing write_queue)
- After submitting to write_queue, tell the user the `proposal_id` for traceability
- Customer sensitive information (contract amounts, personnel evaluations, conflict details) defaults to `Sensitivity: Restricted`; coordinator will hold for review
