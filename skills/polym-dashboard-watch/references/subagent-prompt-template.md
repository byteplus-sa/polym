# Subagent prompt template

Copy-paste template for the `Agent` tool call when spawning a parallel worker to query one batch of customers. Use `subagent_type: general-purpose` and `run_in_background: true`. Send all batch agents in a single assistant message so they run concurrently.

## Template

```
You are a C360 usage-data extractor working one browser tab. Use ONLY the
mcp__Claude_in_Chrome__* tools — no Lark CLI, no file downloads, no network
requests outside Chrome.

Batch: {BATCH_LETTER}
Customers to process: {COUNT}
Customer list file: {ABSOLUTE_PATH_TO_BATCH_JSON}
Date range: {START_DATE} to {END_DATE} (inclusive, local time)
Output file: {ABSOLUTE_PATH_TO_OUTPUT_JSON}

For each customer in the list file (process sequentially, one tab, never
parallel within-batch):

1. Navigate to:
   https://c360.byteintl.net/customer/{crmId}/product-usage/usage?lang=zh-CN
2. Wait for the usage chart to render (canvas + metric cards present).
3. If the page shows "no data" / empty state, write
   {"name": ..., "crmId": ..., "no_data": true}
   and continue to the next customer. Do not retry.
4. Read the three top-metric cards:
   - avg_daily_current_month  (本月日均)
   - mom                      (较上月)
   - avg_daily_selected_range (所选区间日均)
5. Set the date range picker to {START_DATE}..{END_DATE}. If the URL supports
   ?start=&end= params, prefer that over clicking the picker.
6. Read the daily chart values via ECharts getOption() or fiber-walk the
   memoizedProps. Map xAxis.data to series.data per day.
7. If the chart has multiple product lines, SUM them into daily_week and add
   a "notes" field: "Chart shows VLM/LLM/Voice lines; daily_week values are
   <which>+<which> sums (<others>=0 all days)".
8. Format numbers with B/M/K suffixes matching the chart's visible labels.

Output schema (one object per customer, array in the output file):

{
  "name": "<display name>",
  "crmId": "<18-char Salesforce ID>",
  "avg_daily_current_month": "<e.g. 2.54B>",
  "mom": "<e.g. +3.26% or null>",
  "avg_daily_selected_range": "<e.g. 2.69B>",
  "daily_week": {
    "MM-DD": "<value>",
    ...
  }
}

Rules:
- Do not invent or interpolate numbers.
- If chart extraction fails after 2 retries, record
  {"name": ..., "crmId": ..., "error": "<short reason>"} and move on.
- Keep original unit suffixes (B/M/K). Do not convert to raw integers.
- Do not take screenshots unless chart extraction fails.
- Do not spawn sub-subagents.
- Write the output file at the end (single atomic write), not per-customer.

When done, reply with a single-line summary:
"Batch {BATCH_LETTER}: {n_success} ok, {n_no_data} no_data, {n_error} error"
```

## Orchestration checklist (main agent)

- [ ] Decided concurrency (4–6 subagents) based on list size.
- [ ] Split `customers.json` into `customers_batch_A.json`, `_B.json`, … with ≤7 customers per file.
- [ ] Spawned all `Agent` calls in a single message (parallel, `run_in_background: true`).
- [ ] After all complete, `Read` each `batch_*.json` and validate schema.
- [ ] Flag anomalies (zero-usage days, sharp drops, MoM outliers) before composing the report.

## Example: batch file

```json
[
  {"name": "Astria.ai",  "crmId": "001RC00000V65rBYAR"},
  {"name": "EverAI",     "crmId": "001RC00000cE5mjYAC"},
  {"name": "FASHN LTD",  "crmId": "001RC00000f9Wp4YAE"}
]
```

## Example: spawning 4 agents concurrently

In one assistant message, call `Agent` four times. Each call references a
different batch file and output file. Set `run_in_background: true` on all
four. Continue other work while they run; the runtime notifies on completion.
