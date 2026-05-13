---
name: supper-lark-doc-ingest
version: 0.1.1
description: "Scan newly added/modified Lark documents over a time period, automatically extract and ingest into the knowledge base. Default range: yesterday 00:00 to now. Supports ingesting a single specified document. Trigger phrases: '把最近的文档入库', 'lark doc ingest', 'ingest recent docs', 'save this document to knowledge base'."
metadata:
  requires:
    bins: ["lark-cli"]
---

# supper-lark-doc-ingest — Lark Document Ingestion

Scan Lark documents within a time range, extract key content, and write to the knowledge base. Like `supper-im-digest` / `supper-meeting-summary`, saves automatically without interrupting the user.

## Trigger Scenarios

- "Ingest recent documents"
- "Help me organize recent documents"
- "Save this document to the knowledge base" (provide URL)
- "lark doc ingest"
- "Ingest yesterday's Lark documents"
- "把最近的文档入库"
- "帮我整理一下最近的文档"
- "把这个文档存进知识库"

## Parameters

```
supper-lark-doc-ingest                          # Default: yesterday 00:00 to now
supper-lark-doc-ingest --url <lark-doc-url>     # Specify a single document
supper-lark-doc-ingest --days 3                 # Custom time range (days)
supper-lark-doc-ingest --folder <folder-token>  # Restrict to a specific folder
supper-lark-doc-ingest --dry-run                # Preview without writing
```

---

## Complete Execution Flow

### Phase 0 — Preparation

**0.1 Calculate Time Range**

```bash
# macOS
YESTERDAY=$(date -v-1d +%Y-%m-%d)
START_TIME="${YESTERDAY}T00:00:00+08:00"
NOW=$(date +"%Y-%m-%dT%H:%M:%S+08:00")

# Linux
YESTERDAY=$(date -d yesterday +%Y-%m-%d)
```

When the user specifies `--days N`:
```bash
START_TIME=$(date -v-${N}d +%Y-%m-%dT00:00:00+08:00)   # macOS
START_TIME=$(date -d "${N} days ago" +%Y-%m-%dT00:00:00+08:00)  # Linux
```

**0.2 Local Wiki Path Resolution (per `core/local-wiki-ux.md` standard)**

env → memory → detect → ask once (if not found).

**0.3 Load Known Customer List (for classification)**

```bash
grep -h "^# " $LOCAL_WIKI_ROOT/wiki/entities/customers/*.md 2>/dev/null \
  | sed 's/^# //'
```

Also read `aliases` frontmatter. Used for document classification.

---

### Phase 1 — Discover Documents

**Single document mode (`--url` parameter)**

Jump directly to Phase 2; skip discovery.

**Default mode: scan time range**

Run two searches in parallel (merge and deduplicate):

```bash
# Search 1: documents I recently edited
lark-cli drive +search --query "" \
  --edited-since "${YESTERDAY}" \
  --doc-types docx \
  --page-size 20 --format json --as user

# Search 2: recently created documents
lark-cli drive +search --query "" \
  --created-since "${YESTERDAY}" \
  --doc-types docx \
  --page-size 20 --format json --as user
```

If `--folder` is specified, add `--folder-tokens <folder-token>` to both commands.

**Deduplication rule**: keep only one entry per `token`.

**Filtering — skip:**

1. **Already ingested**: check `$LOCAL_WIKI_ROOT/wiki/sources/` for frontmatter containing `doc_id: <token>`
2. **Title blacklist**: purely personal records, temp drafts (`draft-`, `tmp-`)
3. **Content too short**: < 200 characters after Phase 2 read

**Display list** (if > 5 docs, ask for confirmation; 1–3 docs proceed directly):

```
Found <N> documents (<START_DATE> → now)

Will process:
  □ "Acme POC Evaluation Report"   docx · modified 2026-05-12 15:30
  □ "Seedance Competitor Analysis"  docx · modified 2026-05-12 10:00

Will skip (already ingested):
  ✓ "Acme Requirements Doc v2"     ingested on 2026-05-10

Continue? [Y/n] (auto-continues after 5 seconds)
```

---

### Phase 2 — Read & Classify (parallel, max 5 per batch)

**For each document:**

**Step A — Read outline** (low cost; decide before full fetch)

```bash
lark-cli docs +fetch --api-version v2 \
  --doc <token> --scope outline --as user
```

**Step B — Classify** (based on title + outline)

```
1. Title/H1 contains known customer name/alias → "Customer Document"
2. Title contains BytePlus product name         → "Product Document"
3. Title contains competitor name               → "Competitor Document"
4. Title contains "competitor"/"comparison"/"vs"/"analysis" → "Competitor/Analysis Document"
5. Contains "FAQ"/"guide"/"SOP"/"manual"        → "Knowledge Document"
6. Everything else                              → "General Document"
```

**Step C — Read full text** (skip if outline ≤ 3 lines AND no known customer/product)

```bash
lark-cli docs +fetch --api-version v2 \
  --doc <token> --format pretty --as user
```

---

### Phase 3 — Extract Content

| Extraction Item | Method |
|---|---|
| **TL;DR** (3–5 bullets) | Most important conclusions/content |
| **Customers mentioned** | Identify from content vs known list |
| **Products mentioned** | BytePlus product names |
| **People mentioned** | Name + role (if available) |
| **Feature asks** | Explicitly requested functionality |
| **Decisions/conclusions** | Recorded decisions |
| **Competitor information** | Mentions and comparisons |
| **Business information** | Contract/pricing overview (no specific amounts) |

After extraction, run **desensitization check** (supper-sa-wiki `META_DESENSITIZATION` rules):
- Remove AK/SK, tokens, passwords
- Replace customer PII with [redacted]
- Replace contract amounts with "price discussed"

---

### Phase 4 — Write to Local Wiki (Silent)

**Only execute silently when LOCAL_WIKI_ROOT is valid.**

**For each document:**

1. **Save raw content**: `$LOCAL_WIKI_ROOT/raw/doc-<slug>-<YYYY-MM-DD>.md`

2. **Create source page** `wiki/sources/doc-<slug>-<DATE>.md`:
   ```markdown
   ---
   type: source
   kind: doc
   raw_path: raw/doc-<slug>-<DATE>.md
   customer: "[[<customer-slug>]]"
   date: <DATE>
   url: <original Lark URL (strip disposable_login_token)>
   doc_id: <token>
   ---

   # <Document Title>

   ## TL;DR
   - <bullet>

   ## Extracted pages
   - [[<entity-slug>]]

   ## Verbatim quotes worth keeping
   > "<quote>"
   ```

3. **Create/update entity pages** (if applicable):
   - Customer → update Sources and Recent interactions
   - Product → update product page
   - Feature ask → create/update `wiki/concepts/feedback-<slug>.md`
   - Competitor info → update product page Competition section

4. Update `wiki/index.md` + append to `wiki/log.md`

---

### Phase 5 — Write to Lark Wiki

**Execute automatically using supper-sa-wiki skill §5 WRITE workflow.**

- Customer-related → APPEND to `customers/<slug>/TIMELINE`
- Feature ask → CREATE/APPEND feedback page
- New knowledge (concept, SOP, product breakdown) → CREATE topic page
- Competitor document → APPEND to product page competitor section

Run supper-sa-wiki desensitization workflow before writing.

---

### Phase 6 — Closing Report

```
📄  Document ingestion complete (<YESTERDAY> → now)

Found <N> · Ingested <K> · Skipped <M>

Ingestion details:
  ✅ "Acme POC Evaluation Report"   → Customer doc · Updated Acme + created 1 feedback
  ✅ "Seedance Competitor Analysis" → Competitor doc · Updated Seedance product page
  ✅ "BytePlus Compliance Guide"    → Knowledge doc · Created new topic page

Skipped:
  ⏭️ "Today's Notes"              → Content too short
  ⏭️ "Acme Requirements Doc v1"  → Already ingested

Saved <K> entries to knowledge base (<proposal_ids>)
```

---

## Safety Rules

- No content stored before a document is read; fetch failures don't affect other documents
- Desensitization runs before wiki writes; raw content only saved locally in `raw/`
- Documents without read permission are silently skipped (403 → marked `[no permission]` in report)
- Do not use `docs +update` to directly modify wiki pages

## Reference Documents

- [`references/doc-fetch-workflow.md`](references/doc-fetch-workflow.md)
- [`core/local-wiki-ux.md`](../../core/local-wiki-ux.md)
- supper-sa-wiki SKILL.md §5 (WRITE workflow)
