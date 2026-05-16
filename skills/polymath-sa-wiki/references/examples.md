# End-to-End Examples

Concrete walkthroughs for the most common SA Wiki workflows.

---

## Example 1 — Query: "How is customer acme-corp doing lately"

```bash
BASE_TOKEN="UXPdbPJ3kaheZvs2Nc8lLGCcglh"
KI_TABLE="tblLKeA8N3ipyEQv"

# Step 1 — find all rows for this customer
lark-cli base +record-search \
  --base-token $BASE_TOKEN --table-id $KI_TABLE \
  --json '{"filter":{"conjunction":"and","conditions":[
    {"field_name":"Customer","operator":"is","value":["acme-corp"]}
  ]},"page_size":50}' --as user

# Step 2 — read PROFILE first (cheap, gives identity + stage)
lark-cli docs +fetch --api-version v2 --doc <PROFILE_doc_token> --as user

# Step 3 — read TIMELINE
lark-cli docs +fetch --api-version v2 --doc <TIMELINE_doc_token> --as user

# Step 4 — read last 1-2 meeting notes (filter step 1 results by Type=MEETING, Date desc)
```

**Agent answer template:**

> acme-corp is in the [industry] industry, currently at stage [stage]. BANT summary: [from PROFILE].
> Latest event ([most recent date]): [from TIMELINE last entry].
> Key points from last meeting ([date]): [from MEETING note].
> There are [N] open issues / decisions — let me know if you'd like details.

---

## Example 2 — Query: "How do you rotate AK/SK"

```bash
# Step 1 — keyword search across Title + Keywords + Summary
lark-cli base +record-search \
  --base-token $BASE_TOKEN --table-id $KI_TABLE \
  --json '{"filter":{"conjunction":"or","conditions":[
    {"field_name":"Title","operator":"contains","value":["AK/SK"]},
    {"field_name":"Keywords","operator":"contains","value":["AK/SK"]},
    {"field_name":"Keywords","operator":"contains","value":["rotate"]}
  ]},"page_size":10}' --as user

# Step 2 — fetch most relevant page
lark-cli docs +fetch --api-version v2 --doc <doc_token> --as user
```

If no result: "No topic page yet for AK/SK rotation; would you like me to draft one?"

---

## Example 3 — Write: Ingest a meeting note (most common write)

User: "File the kickoff meeting notes from acme-corp into the wiki"

```bash
WQ_TABLE="tblTR65mRdvE74Lu"

# Step 1 — Distill transcript into meeting note format
# (follow page-templates template 4; fetch from $META_PAGE_TEMPLATES)

# Step 2 — Desensitization (fetch $META_DESENSITIZATION)

# Step 3 — CREATE proposal
lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{
    "fields": {
      "SA": "王文杰",
      "action": "CREATE",
      "target_path": "customers/acme-corp/meetings/2026-05-06-kickoff",
      "content_md": "📌 Type: MEETING | Layer: customers | Customer: acme-corp | Date: 2026-05-06\n...",
      "source_refs": "https://...minutes-link",
      "status": "pending"
    }
  }' --as user
# → proposal_id P-00042

# Step 4 — APPEND to TIMELINE
lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{
    "fields": {
      "SA": "王文杰",
      "action": "APPEND",
      "target_path": "customers/acme-corp/TIMELINE",
      "target_doc_token": "<TIMELINE_doc_token>",
      "content_md": "| 2026-05-06 | meeting | Kickoff — initial intro and use-case alignment | [link] |",
      "source_refs": "P-00042",
      "status": "pending"
    }
  }' --as user

# Step 5 — Tell user: "Queued: P-00042 (meeting note) + P-00043 (TIMELINE update)."
```

---

## Example 4 — Write: New topic page (ingest knowledge from chat)

User shared a chat with a Babi SSO workaround. User: "That's useful, add it to the wiki"

```bash
# Step 1 — Verify no duplicate
lark-cli base +record-search --base-token $BASE_TOKEN --table-id $KI_TABLE \
  --json '{"filter":{"conjunction":"and","conditions":[
    {"field_name":"Title","operator":"contains","value":["babi-sso"]}
  ]}}' --as user
# → no result → safe to CREATE

# Step 2 — Distill chat; anonymize personal details

# Step 3 — Submit CREATE
lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{
    "fields": {
      "SA": "王文杰",
      "action": "CREATE",
      "target_path": "topics/access/babi-sso-known-issues",
      "content_md": "📌 Type: FIX | Layer: topics | Domain: access\n   Keywords: Babi, SSO, AK/SK, workaround\n   ...",
      "source_refs": "https://mira.../chat-link",
      "status": "pending"
    }
  }' --as user
# → P-00044
```

---

## Example 5 — Write: Customer onboarding (first time)

New customer "betacorp" entered active POC. User: "Create a customer profile for betacorp"

```bash
# Step 1 — CREATE customer container
lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{"fields":{"SA":"王文杰","action":"CREATE",
    "target_path":"customers/betacorp",
    "content_md":"<h1>betacorp</h1><p>Customer subtree container.</p>",
    "status":"pending"}}' --as user  # → P-00050

# Step 2 — CREATE PROFILE
lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{"fields":{"SA":"王文杰","action":"CREATE",
    "target_path":"customers/betacorp/PROFILE",
    "content_md":"<full PROFILE template content>",
    "status":"pending"}}' --as user  # → P-00051

# Step 3 — CREATE TIMELINE
lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{"fields":{"SA":"王文杰","action":"CREATE",
    "target_path":"customers/betacorp/TIMELINE",
    "content_md":"<TIMELINE template with first row>",
    "status":"pending"}}' --as user  # → P-00052
```

Coordinator processes P-00050 → P-00051 → P-00052 in created_at order.

---

## Example 6 — Cross-link compounding (Karpathy compound)

Agent answered "Customer X has Seedance NSFW false positive" — customer-specific issue linked to a generalizable product problem.

```bash
# 1. CREATE customer issue (real name allowed in customers/)
target_path: customers/X/issues/2026-05-06-seedance-nsfw-false-positive
content_md: "...detailed issue with [Customer X] context..."

# 2. APPEND to product topic page (anonymized)
target_path: topics/products/seedance-known-quality-issues
content_md: "## Known case: NSFW false positive on [a logistics customer] (2026-05)\n..."
```

This is the **compound** mechanism — customer knowledge feeds into general topic knowledge, cross-referenced both ways.

---

## Example 7 — When NOT to write

| User said | Action |
|---|---|
| "That chat was interesting, save it" | Ask: which part is generalizable? Distill first. Don't dump raw chat. |
| "This is our contract amount" | Refuse. Mark Sensitivity:Restricted; reference only. |
| "I talked with the customer about X" | Ask if user wants a meeting note (structured) or just FYI (don't write). |
| "Note the question I just asked the AI" | Don't write. AI session isn't wiki content. |
| "Save this GitHub link" | Ask why — is it a source or just a reference? |

---

## Example 8 — Polling proposal status

```bash
# By record_id (returned at submit time)
lark-cli base +record-get --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --record-id <record_id> --as user

# All pending for this SA
lark-cli base +record-search --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{"filter":{"conjunction":"and","conditions":[
    {"field_name":"SA","operator":"is","value":["王文杰"]},
    {"field_name":"status","operator":"is","value":["pending"]}
  ]}}' --as user
```

States: `pending` → `committed` · `rejected` (see reject_reason, fix and resubmit) · `superseded` (duplicate)

---

## Quick reference

| Task | Command |
|---|---|
| Search by keyword | `+record-search` on knowledge_index, filter Title/Keywords contains |
| Browse domain | `+record-list --view-id $VIEW_DOM_<domain>` |
| Customer summary | Search Customer=name; read PROFILE+TIMELINE |
| Recent changes | `+record-list --view-id $VIEW_ALL` (sorted by Updated desc) |
| New topic page | `+record-upsert` action=CREATE, target_path=topics/X/Y |
| Add meeting note | action=CREATE + APPEND to TIMELINE |
| Update existing | action=APPEND (snippet) or REPLACE (full page, rare) |
| Flag a problem | action=LINT with description in content_md |
