---
name: supper-customer-brief
version: 0.1.1
description: "Pre-meeting customer intelligence snapshot: input a customer name and get a 2-minute briefing in ~30 seconds. Trigger phrases: '帮我备一下 X 的课', 'customer brief X', 'X customer intelligence', 'prep for meeting with X'."
metadata:
  requires:
    bins: ["lark-cli"]
---

# supper-customer-brief — Pre-Meeting Customer Intelligence

**Read-only skill**: aggregates existing data sources to generate an intelligence snapshot; does not trigger any wiki writes.

## Trigger Scenarios

- "Help me prep for my Acme meeting"
- "customer brief Acme"
- "Give me a brief on X before the meeting"
- "Prep for my meeting with X"
- "What should I know about X today?"
- "帮我备一下 Acme 的课"
- "开会前看一下 Acme 的情况"
- "给我一份 X 的 brief"

## Parameters

```
supper-customer-brief <customer name>                 # Default: 14-day activity + 3-way query
supper-customer-brief <customer name> --quick         # Wiki only, ~5 seconds
supper-customer-brief <customer name> --full          # 4-way including C360, ~20 seconds
supper-customer-brief <customer name> --days 7        # Custom activity window (default 14)
supper-customer-brief <customer name> --date tomorrow # Specify meeting date (affects suggestion wording)
```

---

## Execution Flow

### Phase 0 — Parse Input

Extract from user input:
- `CUSTOMER`: customer name (required). If unclear, ask: "Which customer?"
- `DAYS`: activity time window (default 14)
- `MODE`: quick / default / full (default: default)
- `MEETING_DATE`: meeting date (default: today)

Calculate time window:
```bash
# macOS
WINDOW_START=$(date -v-${DAYS}d +%Y-%m-%d)
TODAY=$(date +%Y-%m-%d)
START_TIME="${WINDOW_START}T00:00:00+08:00"
END_TIME="${TODAY}T23:59:59+08:00"
```

**Local wiki path resolution** (per `core/local-wiki-ux.md`): env → memory → detect. If not found, skip local query without prompting (brief is read-only; wiki creation is not forced).

---

### Phase 1 — 4-Way Concurrent Query

**Issue all Agent calls in the same message** (concurrent, not sequential).

#### Query ① — SA Wiki (required)

```
Agent(
  subagent_type="general-purpose",
  description="Query SA Wiki for customer",
  prompt="""
    Query the SA Wiki Bitable for customer: <CUSTOMER>

    Constants (from supper-sa-wiki SKILL.md §3):
    BASE_TOKEN=UXPdbPJ3kaheZvs2Nc8lLGCcglh
    KI_TABLE=tblLKeA8N3ipyEQv

    Steps:
    1. Search knowledge_index for this customer:
       lark-cli base +record-search --base-token $BASE_TOKEN --table-id $KI_TABLE \
         --json '{"filter":{"conjunction":"and","conditions":[
           {"field_name":"Customer","operator":"is","value":["<CUSTOMER>"]}
         ]},"page_size":50}' --format json --as user

    2. From results, identify and fetch (in parallel if possible):
       - PROFILE doc
       - TIMELINE doc (most recent 10 entries)
       - Any open feedback pages (status=open or in-progress)

    Return structured JSON:
    {
      "found": true/false,
      "profile": { stage, region, industry, account_owner, lark_chat, products_in_play[], key_contacts[] },
      "recent_timeline": [ { date, type, summary } ],
      "open_feedback": [ { title, priority, status, product } ],
      "commitments": []
    }
    Return under 400 words. If not found, return {"found": false}.
  """
)
```

#### Query ② — Local Wiki (if LOCAL_WIKI_ROOT exists)

```
Agent(
  subagent_type="general-purpose",
  description="Query local wiki for customer",
  prompt="""
    Read local wiki at <LOCAL_WIKI_ROOT> for customer: <CUSTOMER>

    Steps:
    1. Find customer file: <LOCAL_WIKI_ROOT>/wiki/entities/customers/<slug>.md
    2. Extract: status, lark_chat, Products in play, Recent interactions (last <DAYS> days),
       Open feedback / pain points
    3. Check wiki/sources/ for recent chat/meeting files for this customer

    Return structured JSON:
    {
      "found": true/false,
      "status": "...",
      "lark_chat": "...",
      "recent_interactions": [ { date, type, summary } ],
      "open_pain_points": [ "..." ],
      "recent_source_tldr": [ "..." ]
    }
    Return under 300 words. If not found, return {"found": false}.
  """
)
```

#### Query ③ — Recent IM (default + full mode)

```
Agent(
  subagent_type="general-purpose",
  description="Search recent Lark IM for customer",
  prompt="""
    Search Lark messages for customer: <CUSTOMER>
    Time range: <START_TIME> to <END_TIME>

    Steps:
    1. Find chat_id (use lark_chat from wiki if available,
       otherwise: lark-cli im +chat-search --keyword "<CUSTOMER>" --as user)
    2. Fetch recent messages:
       lark-cli im +chat-messages-list \
         --chat-id <oc_xxx> \
         --start "<START_TIME>" --end "<END_TIME>" \
         --sort asc --page-size 50 --format json --as user
    3. Filter noise; extract: feedback, feature asks, risk signals, competitor mentions,
       unanswered questions

    Return structured JSON:
    {
      "found": true/false,
      "message_count": N,
      "last_active": "YYYY-MM-DD",
      "highlights": [ { "date": "MM-DD", "type": "...", "summary": "..." } ],
      "unanswered_questions": [ "..." ],
      "risk_signals": [ "..." ],
      "competitor_mentions": [ { "name": "...", "context": "..." } ]
    }
    Return under 300 words.
  """
)
```

#### Query ④ — C360 Usage (full mode, Chrome extension ready)

Only triggered in `--full` mode when `mcp__Claude_in_Chrome__list_connected_browsers` returns a non-empty list.

```
Agent(
  subagent_type="general-purpose",
  description="Query C360 usage for customer",
  prompt="""
    Query C360 for customer: <CUSTOMER>
    Use supper-dashboard-watch skill and c360-customer-usage skill pattern.

    Extract: last 30 days total + daily avg, MoM % change, quota remaining %, top product.

    Return: { "found": bool, "monthly_tokens": N, "mom_pct": "+/-N%",
              "quota_remaining_pct": N, "top_product": "...",
              "alert": null | "quota_low" | "usage_drop" | "usage_stop" }
  """
)
```

---

### Phase 2 — Wait and Merge Results

Wait for all agents (timeout 30 seconds). **④ does not block ①②③**.

Merging (see [`references/query-strategy.md`](references/query-strategy.md)):
- Same event in both wiki and IM → keep one, prefer wiki description
- Conflicting info → use IM (more recent), annotate `[wiki may be outdated]`

---

### Phase 3 — Rules Engine: "Suggested Topics for Today"

Deterministic rules — not free-form AI generation:

```
Priority rules (check in order, take first 3 that trigger):

P0 — Must discuss (always first):
  - Quota remaining < 20%       → "Confirm quota renewal plan"
  - Unanswered question > 3 days → "Reply to X's question"
  - Clear risk signal             → "Understand and address competitor consideration"

P1 — Important (raise if applicable):
  - Our commitment > 7 days without follow-up → "Sync progress on [commitment]"
  - Open feedback P0/P1 no update > 14 days  → "Update status of [feedback]"
  - Usage decline MoM < -20%                 → "Understand reason for usage decline"
  - Competitor mention appeared              → "Prepare differentiation vs [competitor]"

P2 — Raise if present:
  - Unconfirmed Feature ask → "Confirm priority/timeline for [ask]"
  - Product update/new feature → "Introduce latest [product] progress"
```

---

### Phase 4 — Output Brief

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  <CUSTOMER> — Pre-Meeting Intelligence  <TODAY>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Quick View]
  Stage: <stage> | Products: <products> | Owner: <account_owner>
  Last contact: <N days ago> (<type>) | Key contact: <name, role>

[Recent Activity]  Last <DAYS> days
  <MM-DD>  <type>  <summary>
  ...(max 6, reverse chronological)

[Open Items]                           (hidden if empty)
  ⚠️  <quota/risk>
  ❓  <unanswered question>
  📋  <open feedback title> (<priority>)

[Our Commitments]                      (hidden if empty)
  → <commitment> (committed <date>, <N> days ago)

[Competitor Radar]                     (hidden if empty)
  <competitor>: <context> (<date>)

[Suggested Topics for Today]
  1. <rule-driven suggestion>
  2. <rule-driven suggestion>
  3. <rule-driven suggestion>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sources: <which sources had data>  |  Mode: <quick/default/full>
```

Empty sections are hidden entirely.

---

### Phase 5 — Optional Follow-up Actions

```
Need more information?
  • Type "deep dive" for the full wiki profile
  • Type "recent meetings" to view recent meeting details
  • Type "C360" to pull usage data (if not shown)
```

---

## Safety Rules

- Read-only operation; no wiki or write_queue writes
- Do not display contract amounts; use trends (+/-N%) for usage figures
- Customer PII (phone/email) not shown in summary but accessible in detail view

## Reference Documents

- [`references/query-strategy.md`](references/query-strategy.md)
- [`core/local-wiki-ux.md`](../../core/local-wiki-ux.md)
- supper-sa-wiki SKILL.md §3 (Bitable constants)
- supper-sa-wiki SKILL.md §4 (READ workflow)
