---
name: polym-dashboard-watch
version: 0.1.1
description: "Query the C360 data dashboard by customer name and specific request, presenting usage trends and insights. Trigger phrases: '查一下客户X的数据', 'dashboard watch', 'X used how many tokens', '看一下X的用量'."
metadata:
  requires:
    bins: ["lark-cli"]
    chrome_extension: true
---

# polym-dashboard-watch — Customer Data Dashboard Query

Query C360 usage data by customer name + specific question, and save valuable insights to the knowledge base.

## Trigger Scenarios

- "Check Acme's data"
- "How many tokens did X use last month"
- "Show me X's usage trend"
- "dashboard watch"
- "Pull X's C360 data"
- "X's monthly usage report"
- "查一下 Acme 的数据"
- "X 上个月用了多少 tokens"
- "帮我拉一下 X 的 C360 数据"

---

## Complete Execution Flow

### Phase 0 — Preparation

**0.1 Parse Input**

Extract from the user's request:
- `customer_name`: customer name (required)
- `query`: specific question (optional, default: last 30 days usage overview)
- `date_range`: time range (optional, default: last 30 days)

If `customer_name` is unclear, ask: "Which customer's data would you like to query?"

**0.2 Local Wiki Path Resolution (per `core/local-wiki-ux.md` standard)**

env → memory → detect → ask once.

**0.3 Check Chrome Extension**

C360 queries are performed via browser automation using the Claude in Chrome extension.

```
Try calling mcp__Claude_in_Chrome__list_connected_browsers
```

- **Extension connected**: display connected browser list, continue
- **Extension not installed / not connected**: proceed to § Chrome Extension Installation Guide

---

## Chrome Extension Installation Guide

When the extension is unavailable, show the user:

```
The Claude for Chrome extension is required to query C360 data.

Installation steps (~2 minutes):

1. Open Chrome and visit the Chrome Web Store, search for "Claude"
   (or ask your team for the internal install link)

2. Click "Add to Chrome" → "Add extension"

3. Pin the Claude extension in Chrome's toolbar

4. In the extension, click "Connect to Claude Code"
   (make sure Claude Code is running)

5. Tell me when done and I'll continue the query.
```

Wait for the user to confirm, then re-check and continue.

---

### Phase 1 — Query C360

Use the browser automation flow from the c360-customer-usage skill (read `~/.claude/skills/c360-customer-usage/SKILL.md`).

**Standard query content:**

```
1. Daily active usage (tokens / API calls) — last 30 days
2. Month-over-month comparison
3. Main product usage distribution
4. Peak usage date and reason (if available)
5. Current balance / quota status
```

**Supplementary queries based on user's specific question:**
- "how many tokens" → exact number + trend
- "MoM growth" → % change
- "what features mainly used" → product breakdown
- "how much balance left" → quota / balance status

---

### Phase 2 — Generate Insights

After obtaining data, identify significant insights:

| Insight Type | Trigger Condition | Recommended Action |
|---|---|---|
| **Usage growth** | MoM > +30% | Understand growth reason, assess expansion need |
| **Usage decline** | MoM < -20% | ⚠️ Risk signal, proactively reach out |
| **Usage stoppage** | ~0 in last 7 days | 🚨 Urgent — something may be wrong |
| **Quota critical** | Balance < 20% | Remind customer to renew or request expansion |
| **Usage spike** | Single day > 3× monthly average | Understand the scenario (batch job? load test?) |
| **New product activated** | First-time usage | Understand use case and support onboarding |

---

### Phase 3 — Output Report

```
📊  <Customer Name> · Data Report (<date range>)

Usage Overview
  Last 30 days total: <N> tokens
  Daily average: <n> tokens
  MoM: <+/-N%> (<last month> → <this month>)

Product Distribution
  <Product A>: <N%>
  <Product B>: <N%>

Quota Status
  Current balance: <N> (<X%> remaining)
  Estimated depletion: <date or "sufficient">

<If insights found>
⚠️  Insight: <insight description>
    Recommendation: <action>
```

**If noteworthy insights are found (decline, stoppage, quota critical), ask:**

"Found some data worth noting. Save to knowledge base? [Y/n]"

- Y / Enter: proceed to write flow
- N: finish, do not write

> Pure number queries ("how many tokens did X use") do not trigger this prompt.

---

### Phase 4 — Write to Knowledge Base

**Only executed when the user confirms.**

**Local wiki (silent):**

Update `wiki/entities/customers/<slug>.md`:
- Append line under `## Recent interactions`: "<TODAY> · dashboard · <one-line insight>"
- Usage decline/stoppage → annotate risk under `## Open feedback / pain points`

**Lark wiki (via polym-sa-wiki WRITE workflow):**

- APPEND TIMELINE: "<TODAY> | dashboard | <insight summary> | quota: <status>"
- Quota critical → CREATE/APPEND related reminder

After writing, show `Saved to knowledge base` in the report (no write details exposed).

---

### Phase 5 — Closing

```
✅  <Customer Name> data query complete

<Insight summary (if any)>

<If written> Saved to knowledge base (<proposal_id>)
```

---

## Safety Rules

- Do not write specific contract amounts / ARR figures to wiki
- Do not retain screenshot files after the browser session
- Do not use `docs +update` to directly modify wiki pages

## Reference Documents

- [`references/c360-query.md`](references/c360-query.md)
- [`core/local-wiki-ux.md`](../../core/local-wiki-ux.md)
