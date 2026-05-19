# Query a customer's product-usage data

Each subagent owns one Chrome tab and works through a batch of customers. This doc describes what to do inside that tab for a single customer.

## URL pattern

```
https://c360.byteintl.net/customer/{CrmAccountId}/product-usage/usage
```

`{CrmAccountId}` is the 18-char Salesforce ID from the customer list (e.g. `001RC00000V65rBYAR`).

## Workflow per customer

### 1. Navigate

```
mcp__Claude_in_Chrome__navigate
  url: https://c360.byteintl.net/customer/001RC00000V65rBYAR/product-usage/usage
```

Wait until the page stabilizes. A reliable readiness signal:

```javascript
mcp__Claude_in_Chrome__javascript_tool
  code: |
    const metric = document.querySelector('[class*="usageCard"]') ||
                   document.querySelector('[class*="metric"]');
    const chart = document.querySelector('.echarts-for-react canvas') ||
                  document.querySelector('canvas[data-zr-dom-id]');
    return { metricReady: !!metric, chartReady: !!chart };
```

If the page shows an empty state ("No usage data" / "暂无数据"), record `{no_data: true}` and move on. Do **not** spend time retrying.

### 2. Set the date range

The date range selector is an Ant Design `RangePicker`. Programmatic setting is more robust than clicking:

- Either click the picker and type the dates (`keyboard` / `fill` tools).
- Or dispatch React's onChange via the fiber:

```javascript
mcp__Claude_in_Chrome__javascript_tool
  code: |
    // Find the picker element and the onChange handler on its fiber
    const picker = document.querySelector('.ant-picker');
    if (!picker) return { error: 'picker not found' };
    // fallback: click + keyboard type via separate tool calls
    picker.click();
```

**Easier alternative**: most C360 charts let you set a range via URL query parameters (`?start=YYYY-MM-DD&end=YYYY-MM-DD`). Inspect the request in the network panel once, then encode it in the navigate URL for subsequent customers in the same batch.

### 3. Read the top metrics

Above the chart C360 shows three headline numbers per product:

| Label | Example | JSON field |
|---|---|---|
| 本月日均 Avg daily (current month) | `2.54B` | `avg_daily_current_month` |
| 较上月 MoM change | `+3.26%` | `mom` |
| 所选区间日均 Avg daily (selected range) | `2.69B` | `avg_daily_selected_range` |

These are plain text in the DOM — extract via querySelector or fiber walk:

```javascript
mcp__Claude_in_Chrome__javascript_tool
  code: |
    const cards = document.querySelectorAll('[class*="metricCard"], [class*="usageCard"]');
    const out = {};
    cards.forEach(card => {
      const label = card.querySelector('[class*="label"], [class*="title"]')?.textContent?.trim();
      const value = card.querySelector('[class*="value"], [class*="number"]')?.textContent?.trim();
      if (label && value) out[label] = value;
    });
    return out;
```

Labels shift between locales (zh-CN vs en). Always append `?lang=zh-CN` or `?lang=en` to the navigate URL to force one, so the label keys are stable within a batch.

### 4. Read the daily chart

The chart is ECharts. Two reliable extraction paths:

**(a) Grab ECharts instance directly** — preferred when the chart exposes an instance:

```javascript
mcp__Claude_in_Chrome__javascript_tool
  code: |
    const canvases = document.querySelectorAll('canvas[data-zr-dom-id]');
    const results = [];
    for (const c of canvases) {
      const chartEl = c.closest('.echarts-for-react, [_echarts_instance_]');
      if (!chartEl) continue;
      const id = chartEl.getAttribute('_echarts_instance_');
      const inst = window.echarts?.getInstanceById?.(id);
      if (!inst) continue;
      const opt = inst.getOption();
      results.push({
        xAxis: opt.xAxis?.[0]?.data,
        series: opt.series?.map(s => ({ name: s.name, type: s.type, data: s.data })),
      });
    }
    return results;
```

**(b) Walk fiber to find the data prop** — fallback when `window.echarts` isn't exposed:

```javascript
mcp__Claude_in_Chrome__javascript_tool
  code: |
    const el = document.querySelector('.echarts-for-react');
    const key = Object.keys(el).find(k => k.startsWith('__reactFiber'));
    let fiber = el[key];
    while (fiber) {
      const p = fiber.memoizedProps;
      if (p && p.option && p.option.series) return p.option;
      fiber = fiber.return;
    }
    return null;
```

### 5. Map chart output to the expected schema

ECharts `series[i].data` is typically `[{value: 2280000000, ...}, ...]` or `[2280000000, 3260000000, ...]`. Zip with `xAxis.data` (e.g. `["04-13", "04-14", ...]`) and format:

```javascript
// Map raw numbers to "2.28B" style to match the chart's displayed values.
// Keep B/M/K suffixes — the consolidator prefers them.
function humanize(n) {
  if (n >= 1e9) return (n / 1e9).toFixed(2).replace(/\.?0+$/, '') + 'B';
  if (n >= 1e6) return (n / 1e6).toFixed(2).replace(/\.?0+$/, '') + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(2).replace(/\.?0+$/, '') + 'K';
  return String(n);
}
```

### 6. Multi-series charts (VLM / LLM / Voice, etc.)

Some customers have multiple product lines. If the chart has >1 series:

- Sum the values per day into `daily_week`.
- Add a `notes` field: `"Chart shows VLM/LLM/Voice lines; daily_week values are VLM+LLM sums (Voice=0 all days)"`.
- Never silently drop a series.

## Common pitfalls

| Pitfall | Fix |
|---|---|
| Chart not yet rendered, `getOption()` returns `null` | Wait for `canvas` element then 500ms; retry up to 3x |
| Navigating between customers leaves stale chart data | Always wait for the URL to update (check `location.pathname` matches) before reading |
| Locale-dependent label keys | Pin `?lang=zh-CN` in navigate URL for an entire batch |
| Virtualized chart range exceeded | Date picker range silently clamps to 3 months; verify `xAxis.data.length` matches expected day count |
| Values look off by 1000× | ECharts raw numbers are in base units; confirm unit suffix matches the chart's y-axis |

## Graceful degradation

If a customer's chart can't be read programmatically after 2 retries, the subagent should write:

```json
{
  "name": "...",
  "crmId": "...",
  "error": "chart unreadable after 2 retries",
  "fallback_screenshot": "path/to/screenshot.png"
}
```

…and take a screenshot (`mcp__Claude_in_Chrome__gif_creator` or `screenshot`) so the main agent can read it manually. Do not invent data.
