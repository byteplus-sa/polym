# End-to-End Examples

Concrete walkthroughs for the most common SA Wiki workflows.

---

## Example 1 — Query: "客户 acme-corp 最近怎么样"

User asks the agent for a summary of customer acme-corp.

```bash
# Set constants
BASE_TOKEN="UXPdbPJ3kaheZvs2Nc8lLGCcglh"
KI_TABLE="tblLKeA8N3ipyEQv"

# Step 1 — find all rows for this customer
lark-cli base +record-search \
  --base-token $BASE_TOKEN \
  --table-id $KI_TABLE \
  --json '{
    "filter": {
      "conjunction": "and",
      "conditions": [
        {"field_name": "Customer", "operator": "is", "value": ["acme-corp"]}
      ]
    },
    "page_size": 50
  }' \
  --as user
# → returns rows for PROFILE, TIMELINE, multiple meetings, issues, decisions

# Step 2 — read PROFILE first (cheap, gives identity + stage)
lark-cli docs +fetch --api-version v2 --doc <PROFILE_doc_token> --as user

# Step 3 — read TIMELINE (gives chronology in one page)
lark-cli docs +fetch --api-version v2 --doc <TIMELINE_doc_token> --as user

# Step 4 — for "recent", read last 1-2 meeting notes by Date
# (filter results from step 1 by Type=MEETING, sort by Date desc; fetch top 2)
```

**Agent answer template:**

> acme-corp 是 [industry] 行业，目前处于 [stage]。BANT 简况：[from PROFILE]。
> 最近事件（[最近日期]）：[from TIMELINE 最后一条]。
> 最近一次会议（[date]）的关键点：[from MEETING note]。
> 还有 [N] 个 open issues / decisions，需要看详情请告诉我。

---

## Example 2 — Query: "AK/SK 怎么轮换"

User has a topic question. No customer involved.

```bash
# Step 1 — keyword search across Title + Keywords + Summary
lark-cli base +record-search \
  --base-token $BASE_TOKEN \
  --table-id $KI_TABLE \
  --json '{
    "filter": {
      "conjunction": "or",
      "conditions": [
        {"field_name": "Title", "operator": "contains", "value": ["AK/SK"]},
        {"field_name": "Keywords", "operator": "contains", "value": ["AK/SK"]},
        {"field_name": "Keywords", "operator": "contains", "value": ["rotate"]}
      ]
    },
    "page_size": 10
  }' \
  --as user
# → returns 1-3 most relevant rows (filter to Layer=topics for clean results)

# Step 2 — fetch the most relevant page
lark-cli docs +fetch --api-version v2 --doc <doc_token> --as user

# Step 3 — synthesize answer from the Steps section
```

If no result: tell user "no topic page yet for AK/SK rotation; would you like me to draft one?" — and proceed to write workflow if they say yes.

---

## Example 3 — Write: Ingest a meeting note (most common write)

User: "把这次和 acme-corp 的 kickoff 会议纪要整理进 wiki"

```bash
WQ_TABLE="tblTR65mRdvE74Lu"

# Step 1 — Distill the raw transcript / minutes into structured meeting note format
# (Agent does this in its own working memory, follow wiki page-templates (fetch from $META_PAGE_TEMPLATES) template 4)

# Step 2 — Run desensitization checks on the distilled content (wiki desensitization checklist (fetch from $META_DESENSITIZATION))

# Step 3 — Submit CREATE proposal for the meeting note
lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{
    "fields": {
      "agent_id": "sa-wenjie",
      "action": "CREATE",
      "target_path": "customers/acme-corp/meetings/2026-05-06-kickoff",
      "content_md": "📌 Type: MEETING | Layer: customers | Domain: meeting | Customer: acme-corp | Date: 2026-05-06\n   Keywords: kickoff, intro, vision-ai\n   Sensitivity: Internal | Updated: 2026-05-06\n   Source_refs: <minutes URL>\n\n# acme-corp — Kickoff — 2026-05-06\n\n## Attendees\n...\n\n## Agenda\n...\n\n## Discussion\n...\n\n## Decisions\n...\n\n## Action items\n...",
      "source_refs": "https://...minutes-link",
      "status": "pending"
    }
  }' \
  --as user
# → returns proposal_id like P-00042

# Step 4 — Submit APPEND to TIMELINE (link the new meeting in the customer's timeline)
lark-cli base +record-search --base-token $BASE_TOKEN --table-id $KI_TABLE \
  --json '{"filter":{"conjunction":"and","conditions":[{"field_name":"Title","operator":"is","value":["customers/acme-corp/TIMELINE"]}]}}' \
  --as user
# → get TIMELINE doc_token

lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{
    "fields": {
      "agent_id": "sa-wenjie",
      "action": "APPEND",
      "target_path": "customers/acme-corp/TIMELINE",
      "target_doc_token": "<TIMELINE_doc_token>",
      "content_md": "| 2026-05-06 | meeting | Kickoff — initial intro and use-case alignment | [link to meeting note] |",
      "source_refs": "P-00042",
      "status": "pending"
    }
  }' \
  --as user

# Step 5 — Tell user
# "已入队：proposal_id=P-00042 (meeting note) + P-00043 (TIMELINE update). 
#  Coordinator commit 后会自动出现在 wiki 里，你可以在 02 · DATA → write_queue → Pending only view 看实时状态。"
```

---

## Example 4 — Write: New topic page (ingest knowledge from chat)

User shared a Mira chat where someone explained a Babi SSO workaround. User: "这条信息不错，加到 wiki 里"

```bash
# Step 1 — Verify no duplicate
lark-cli base +record-search --base-token $BASE_TOKEN --table-id $KI_TABLE \
  --json '{"filter":{"conjunction":"and","conditions":[{"field_name":"Title","operator":"contains","value":["babi-sso"]}]}}' \
  --as user
# → no result (good, can CREATE)

# Step 2 — Distill chat into topic format (template 1 in wiki page-templates ($META_PAGE_TEMPLATES))
# Anonymize any personal details from the chat

# Step 3 — Submit CREATE
lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{
    "fields": {
      "agent_id": "sa-wenjie",
      "action": "CREATE",
      "target_path": "topics/access/babi-sso-known-issues",
      "content_md": "📌 Type: FIX | Layer: topics | Domain: access\n   Keywords: Babi, SSO, AK/SK, cannot create, workaround\n   Sensitivity: Internal | Updated: 2026-05-06\n   Source_refs: <chat URL or distilled note>\n\n# Babi SSO — Known issues and workarounds\n\n## Context\nUsers signing into BytePlus Console via Babi SSO sometimes cannot directly create AK/SK pairs.\n\n## Symptom\n[symptom details]\n\n## Root cause\n[explanation]\n\n## Workaround\n1. ...\n2. ...\n\n## Permanent fix\nTracked in [ticket]; ETA [date].\n\n## Escalation\nPlatform on-call.",
      "source_refs": "https://mira.../chat-link",
      "status": "pending"
    }
  }' \
  --as user
# → P-00044

# Step 4 — also consider APPEND to topics/access page if you want a link there
```

---

## Example 5 — Write: Customer onboarding (first time)

New customer "betacorp" entered active POC. User: "新建 betacorp 的客户档案"

```bash
# Step 1 — CREATE customer container (sets up the parent node)
lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{
    "fields": {
      "agent_id": "sa-wenjie",
      "action": "CREATE",
      "target_path": "customers/betacorp",
      "content_md": "<h1>betacorp</h1>\n<p>Customer subtree container.</p>",
      "status": "pending"
    }
  }' \
  --as user
# → P-00050

# Step 2 — CREATE PROFILE (template 2)
lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{
    "fields": {
      "agent_id": "sa-wenjie",
      "action": "CREATE",
      "target_path": "customers/betacorp/PROFILE",
      "content_md": "<full PROFILE template content>",
      "status": "pending"
    }
  }' \
  --as user
# → P-00051

# Step 3 — CREATE TIMELINE (template 3) — initial entry
lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{
    "fields": {
      "agent_id": "sa-wenjie",
      "action": "CREATE",
      "target_path": "customers/betacorp/TIMELINE",
      "content_md": "<TIMELINE template with first row: today, milestone, customer onboarded>",
      "status": "pending"
    }
  }' \
  --as user
# → P-00052
```

**Coordinator processes in order P-00050 → P-00051 → P-00052** (respecting created_at sequencing).

---

## Example 6 — Cross-link compounding (Karpathy compound)

Agent answered a query about "客户 X has Seedance NSFW false positive". The answer required linking the customer's specific issue to a generalizable Seedance problem.

**Two writes in one workflow:**

```bash
# 1. CREATE customer issue (real customer name in customers/)
target_path: customers/X/issues/2026-05-06-seedance-nsfw-false-positive
content_md: "...detailed issue with [Customer X] context..."

# 2. APPEND to topics/products/seedance-known-quality-issues (anonymized reference)
target_path: topics/products/seedance-known-quality-issues
target_doc_token: <existing topic page>
content_md: "## Known case: NSFW false positive on [a logistics customer] (2026-05)
Symptom: [...]
Root cause: classifier threshold too strict for prompts with athletic content.
See customer-side detail: <link to issue page>"
```

This is the **compound** mechanism in action — customer-specific knowledge feeds back into general topic knowledge, with cross-references both ways.

---

## Example 7 — When to NOT write

Agent recognizes that not all info should go into wiki:

| User said | Action |
|---|---|
| "刚才的 chat 还挺有意思的，存一下" | Ask: which part is generalizable? Distill to topic / customer issue. Don't dump raw chat. |
| "这是我们的合同金额" | Refuse. Mark Sensitivity:Restricted on related decision page; reference only. |
| "我和客户聊了什么什么" | Ask if user wants meeting note (structured) or just FYI (don't write). |
| "记一下我刚才问 AI 的问题" | Don't write. AI session content isn't wiki content unless it produced a generalizable insight. |
| "把这个 GitHub 链接保存一下" | Ask why — is it a source (sources/policy-docs?) or a reference (just leave the link in chat)? |

---

## Example 8 — Polling proposal status

After submitting, user asks "我那个提议处理了吗？"

```bash
# Get the specific record by record_id (returned at submit time)
lark-cli base +record-get --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --record-id <record_id> --as user

# Or list all pending for this agent
lark-cli base +record-search --base-token $BASE_TOKEN --table-id $WQ_TABLE \
  --json '{
    "filter": {
      "conjunction": "and",
      "conditions": [
        {"field_name": "agent_id", "operator": "is", "value": ["sa-wenjie"]},
        {"field_name": "status", "operator": "is", "value": ["pending"]}
      ]
    }
  }' --as user
```

Common states:
- `pending` — waiting for coordinator
- `committed` — done, see wiki
- `rejected` — see reject_reason field, fix and resubmit
- `superseded` — duplicate; another agent's proposal won

---

## Quick reference

| Task | Path |
|---|---|
| Search by keyword | `+record-search` on knowledge_index, filter Title/Keywords contains |
| Browse domain | `+record-list` with `--view-id $VIEW_DOM_<domain>` |
| Customer summary | `+record-search` filter Customer=name; read PROFILE+TIMELINE |
| Recent changes | `+record-list` with `--view-id $VIEW_ALL` (already sorted by Updated desc) |
| New topic page | `+record-upsert` on write_queue, action=CREATE, target_path=topics/X/Y |
| Add meeting note | `+record-upsert` action=CREATE + APPEND to TIMELINE |
| Update existing | action=APPEND (snippet) or REPLACE (whole page, rare) |
| Flag a problem | action=LINT with description in content_md |
