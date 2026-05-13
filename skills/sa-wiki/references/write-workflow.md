# Write Workflow

**Mandatory**: every wiki write goes through `write_queue`. Never `docs +update` a wiki page directly.

## Workflow

```
Decide action (CREATE / APPEND / REPLACE / LINT)
       ↓
Build content_md (follow page templates fetched from wiki: $META_PAGE_TEMPLATES)
       ↓
Run desensitization checklist (fetch from wiki: $META_DESENSITIZATION)
       ↓
Insert row into write_queue (status=pending)
       ↓
Coordinator picks it up → commits to wiki → writes log row
       ↓
Tell user the proposal_id; they can poll or wait for commit
```

---

## Action: CREATE (new page)

Use when target_path does not yet exist.

```bash
# Step 1: Verify target_path doesn't exist
lark-cli base +record-search --base-token $BASE_TOKEN --table-id $KI_TABLE \
  --json '{"filter":{"conjunction":"and","conditions":[
    {"field_name":"Title","operator":"is","value":["topics/access/ak-sk-lifecycle"]}
  ]}}' --as user
# Should return zero rows. If not zero, switch to APPEND or REPLACE.

# Step 2: Desensitization — fetch the latest checklist from wiki
#   lark-cli docs +fetch --api-version v2 --doc $META_DESENSITIZATION --as user

# Step 3: Submit CREATE proposal
lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{
    "fields": {
      "agent_id": "sa-wenjie",
      "action": "CREATE",
      "target_path": "topics/access/ak-sk-lifecycle",
      "target_doc_token": "",
      "content_md": "<full markdown content following the topic page template>",
      "source_refs": "https://...",
      "status": "pending"
    }
  }' --as user

# Step 4: Capture returned record_id and proposal_id (P-XXXXX) — share with user
```

**Required fields**: agent_id, action, target_path, content_md, status
**Empty fields**: target_doc_token (set by coordinator after creation)
**Recommended**: source_refs

---

## Action: APPEND (add to existing page)

Use when adding new info to an existing page (e.g., new TIMELINE entry, new topic sub-section).

```bash
# Step 1: Look up target_doc_token by target_path
lark-cli base +record-search --base-token $BASE_TOKEN --table-id $KI_TABLE \
  --json '{"filter":{"conjunction":"and","conditions":[
    {"field_name":"Title","operator":"is","value":["customers/acme-corp/TIMELINE"]}
  ]}}' --as user
# → returns the doc_token field value

# Step 2: Submit APPEND proposal
lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{
    "fields": {
      "agent_id": "sa-wenjie",
      "action": "APPEND",
      "target_path": "customers/acme-corp/TIMELINE",
      "target_doc_token": "<doc_token from step 1>",
      "content_md": "| 2026-05-06 | meeting | Pricing alignment with finance | [link] |",
      "source_refs": "<meeting note doc_token or URL>",
      "status": "pending"
    }
  }' --as user
```

**Notes:**
- `content_md` is the snippet to append, NOT the full new page
- Coordinator appends after the last block, preserving existing content
- For TIMELINE table rows: provide the table row markdown only

---

## Action: REPLACE (overwrite existing page)

Use rarely. Only when the entire page needs to change.

```bash
lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{
    "fields": {
      "agent_id": "sa-wenjie",
      "action": "REPLACE",
      "target_path": "topics/access/ak-sk-lifecycle",
      "target_doc_token": "<existing doc_token>",
      "content_md": "<full new page body>",
      "source_refs": "<reason / source>",
      "status": "pending"
    }
  }' --as user
```

**Coordinator validation:**
- REPLACE requires target's `last_committed_at` to be older than the proposal's `created_at`
- Conflict → auto-reject: "concurrent commit; re-fetch and retry"

---

## Action: LINT (request cleanup)

Flag a problem for the coordinator to handle.

```bash
lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{
    "fields": {
      "agent_id": "sa-wenjie",
      "action": "LINT",
      "target_path": "topics/products/seedance-whitelist",
      "content_md": "Last-updated > 90 days ago; whitelist section claims pre-GA but Seedance 2.0 is now GA. Please update.",
      "status": "pending"
    }
  }' --as user
```

---

## Customer subtree on first encounter

```
1. CREATE customers/<name>/PROFILE     ← BANT, contacts, stage
2. CREATE customers/<name>/TIMELINE    ← initial entry
3. (later) APPEND TIMELINE for each event
4. (per meeting) CREATE customers/<name>/meetings/<YYYY-MM-DD>-<slug>
5. (as needed) CREATE customers/<name>/issues/...  decisions/...
```

For first PROFILE/TIMELINE: coordinator auto-creates intermediate parent nodes. Or CREATE the parent container first:

```bash
lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{"fields":{"agent_id":"sa-wenjie","action":"CREATE",
    "target_path":"customers/acme-corp",
    "content_md":"<h1>acme-corp</h1><p>Customer subtree container.</p>",
    "status":"pending"}}' --as user
```

---

## After committing — what changes

1. New / updated wiki page (CREATE / APPEND / REPLACE)
2. New row in `knowledge_index` Bitable (or updated Updated field)
3. New row in `log` table: ts, action, target_path, doc_token, agent_id, SA, proposal_id
4. write_queue row: status=committed, committed_at=now

```bash
# Poll the proposal's status
lark-cli base +record-get --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --record-id <returned_record_id> --as user
```

---

## Common rejection reasons

| reject_reason | Meaning | Fix |
|---|---|---|
| "duplicate target_path; use APPEND or REPLACE" | CREATE but target exists | Re-submit with APPEND or REPLACE |
| "desensitization failed: contains apparent AK/SK pattern" | Credential detected | Redact; re-submit |
| "desensitization failed: customer real name in topics/" | Real name in topics/ page | Replace with [Customer A]; re-submit |
| "concurrent commit; re-fetch and retry" | REPLACE conflict | Re-fetch target, re-merge, re-submit |
| "naming violation: target_path does not match conventions" | Bad target_path format | See SKILL.md §6; re-submit |
| "unknown domain" | Domain not in known list | Use one of: access / security / product / poc / ops / onboarding / customer |
| "Sensitivity=Restricted requires manual review" | High-sensitivity content | Wait for human SA review |

---

## Best practices for content_md

1. **Always start with the metadata callout block** — Type / Layer / Domain / Keywords / Sensitivity / Updated / Source_refs
2. **Use page templates** — fetch `$META_PAGE_TEMPLATES` before writing
3. **Paraphrase external sources** — don't copy-paste large chunks verbatim
4. **Cross-link** — link to other wiki pages with wiki URLs
5. **No raw chat dumps** — distill into points
6. **Idempotent** — re-running CREATE/REPLACE produces the same result

---

## What NOT to do

- ❌ Don't `lark-cli docs +update` directly on wiki pages (bypasses queue, breaks audit)
- ❌ Don't write `target_doc_token` for CREATE actions
- ❌ Don't submit multiple pending CREATEs for the same target_path
- ❌ Don't put real customer names in topics/ pages (use [Customer A])
- ❌ Don't include AK/SK / passwords / tokens / contract amounts
- ❌ Don't ingest L4-classified content as full text
