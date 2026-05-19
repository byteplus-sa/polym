# C360 Query Reference

## Overview

C360 (Customer 360) is BytePlus's internal customer data platform.
Queries are performed via Chrome browser automation using the Claude in Chrome extension.

This file is the entry point for the browser-automation flow used by
`polym-dashboard-watch`. The detailed runbooks live in sibling files in this
same `references/` directory — no external skill is required.

---

## Chrome Extension Check

```
# Try to list connected browsers — if this fails, extension not installed
mcp__Claude_in_Chrome__list_connected_browsers
```

Expected response when connected:
```json
[{"id": "...", "title": "...", "url": "..."}]
```

Empty array or error → guide user through installation (see SKILL.md § Chrome Extension Installation Guide).

---

## Workflow at a glance

```
Customer list  ──► extract CrmAccountIds  ──► save to customers.json
                                                    │
                                                    ▼
                              split into batches (5-6 customers each)
                                                    │
                                                    ▼
                          spawn N parallel subagents (general-purpose, bg)
                                                    │
                                                    ▼
             each subagent: open tab → navigate to detail → read chart data
                                                    │
                                                    ▼
                                  batch_A.json … batch_N.json
                                                    │
                                                    ▼
                              main agent consolidates into report
```

Single-customer queries (the common case for polym-dashboard-watch) skip the
batching and run steps 1, 3, 4 directly in the main tab.

---

## Detailed runbooks

| Step | File | What it covers |
|---|---|---|
| 1. List | [`customer-list-extraction.md`](customer-list-extraction.md) | React-fiber walk to pull `CrmAccountId` from the customer table |
| 2. Plan | [`subagent-prompt-template.md`](subagent-prompt-template.md) | Batch sizing, copy-paste subagent prompt, output schema |
| 3. Query | [`customer-usage-query.md`](customer-usage-query.md) | Detail-page navigation, date picker, ECharts data extraction |

For a single-customer query:
- Skip step 2 (no subagents).
- Step 1 reduces to a name → `CrmAccountId` lookup; if the user gave a name only, navigate to the list URL once and find the row, or use the saved `crmId` from local wiki / prior runs.

---

## Data points to extract

| Field | Where in C360 | Notes |
|---|---|---|
| Daily tokens | Usage chart | Last 30 days, daily granularity |
| Monthly total | Summary card | Current month + last month |
| MoM % change | Summary card / computed | Displayed as `+3.26%` |
| Product breakdown | Product usage tab | % per product |
| Quota / balance | Account tab | Remaining quota % |
| Account ID | Account info | 10-digit IAM account ID |

---

## Customer name lookup

If the customer name doesn't match exactly in C360:
1. Try partial name match.
2. Try company alias (from local wiki `aliases` frontmatter, if available).
3. If you only have a 10-digit IAM account ID (and not a customer name), search the C360 customer list (`?tab=all`) for the matching `AccountId` column. The `seedance-account-lookup` skill, if installed, does the same reverse lookup faster — but it's not required.

---

## Insight thresholds

| Metric | Threshold | Severity |
|---|---|---|
| MoM growth | > +30% | Info |
| MoM decline | < -20% | ⚠️ Warning |
| MoM decline | < -50% | 🚨 Critical |
| 7-day active usage | < 5% of monthly avg | 🚨 Critical |
| Quota remaining | < 20% | ⚠️ Warning |
| Quota remaining | < 5% | 🚨 Critical |
| Single-day spike | > 3× monthly daily avg | Info |

---

## Error handling

| Situation | Action |
|---|---|
| Customer not found in C360 | Ask user to confirm spelling; try aliases |
| C360 page load timeout | Retry once; if fails, tell user C360 may be slow |
| No data for date range | Report "no usage data found for this period" |
| Extension disconnected mid-query | Re-check extension, ask user to reconnect |
