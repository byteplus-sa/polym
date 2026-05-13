# C360 Query Reference

## Overview

C360 (Customer 360) is BytePlus's internal customer data platform.
Queries are performed via Chrome browser automation using the Claude in Chrome extension.

The `c360-customer-usage` skill (in `~/.claude/skills/c360-customer-usage/`) contains
the detailed browser automation runbook. This file documents how supper-dashboard-watch
calls into it.

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

Empty array or error → guide user through installation (see SKILL.md § Chrome Extension Setup).

---

## Invoking c360-customer-usage

supper-dashboard-watch delegates all C360 browser automation to the `c360-customer-usage` skill.

Read `~/.claude/skills/c360-customer-usage/SKILL.md` and follow its instructions for:
1. Navigating to C360
2. Searching for the customer by name
3. Extracting usage data
4. Handling pagination and date range filters

Do not duplicate the browser automation logic here.

---

## Data Points to Extract

| Field | Where in C360 | Notes |
|---|---|---|
| Daily tokens | Usage chart | Last 30 days, daily granularity |
| Monthly total | Summary card | Current month + last month |
| MoM % change | Computed from monthly totals | |
| Product breakdown | Product usage tab | % per product |
| Quota / balance | Account tab | Remaining quota % |
| Account ID | Account info | 10-digit IAM account ID |

---

## Customer Name Lookup

If the customer name doesn't match exactly in C360:
1. Try partial name match
2. Try company alias (from local wiki `aliases` frontmatter if available)
3. Try `~/.claude/skills/seedance-account-lookup/` if need to look up by account ID

---

## Insight Thresholds

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

## Error Handling

| Situation | Action |
|---|---|
| Customer not found in C360 | Ask user to confirm spelling; try aliases |
| C360 page load timeout | Retry once; if fails, tell user C360 may be slow |
| No data for date range | Report "no usage data found for this period" |
| Extension disconnected mid-query | Re-check extension, ask user to reconnect |
