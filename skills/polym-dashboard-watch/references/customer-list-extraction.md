# Extract customer list from C360

C360 renders its customer table with React + Ant Design. The table rows don't carry their Salesforce `CrmAccountId` in the DOM attributes — the ID lives in React props on each row's fiber node. This guide shows how to extract it reliably.

## 1. Navigate to the list

```
mcp__Claude_in_Chrome__navigate
  url: https://c360.byteintl.net/customer/list?lang=zh-CN&tab=collaborative_account
```

Common tabs:

| Tab | URL | Typical size |
|---|---|---|
| All accounts | `?tab=all` | 1000+, paginated |
| Collaborative | `?tab=collaborative_account` | ~20-30 per user |
| Favorite | `?tab=favorite_account` | user's shortlist |

**Do not** click the tab in the UI — the URL parameter sometimes doesn't update, which makes retries inconsistent. Navigate directly to the URL.

## 2. Wait for the table to hydrate

After navigation, the table renders client-side. Wait until at least one data row exists:

```javascript
mcp__Claude_in_Chrome__javascript_tool
  code: |
    const rows = document.querySelectorAll('tr[data-row-key]');
    return { ready: rows.length > 0, count: rows.length };
```

If `ready: false`, wait ~1.5s and retry. Timeout after ~10s and surface an error.

## 3. Walk React fibers to extract CrmAccountId

Ant Design tables stash the row record on the fiber node under `memoizedProps.children[0].props.record`. The field name is `CrmAccountId` (18-char Salesforce ID, e.g. `001RC00000XXXXXYYYY`).

```javascript
mcp__Claude_in_Chrome__javascript_tool
  code: |
    const rows = Array.from(document.querySelectorAll('tr[data-row-key]'));
    const out = [];
    for (const row of rows) {
      const fiberKey = Object.keys(row).find(k => k.startsWith('__reactFiber'));
      if (!fiberKey) continue;
      let fiber = row[fiberKey];
      // Climb up to find the node whose memoizedProps has `record`
      let record = null;
      while (fiber) {
        const props = fiber.memoizedProps;
        if (props && props.record && props.record.CrmAccountId) {
          record = props.record;
          break;
        }
        fiber = fiber.return;
      }
      if (record) {
        out.push({
          name: record.Name || record.AccountName || '',
          cid: record.Cid || record.AccountCode || '',
          crmId: record.CrmAccountId,
        });
      }
    }
    return out;
```

Field names observed:
- `Name` / `AccountName` — display name
- `Cid` / `AccountCode` — `ACC-XXXXXXXXXX` internal code (optional)
- `CrmAccountId` — **required**, the 18-char Salesforce ID

## 4. Paginate if needed

Collaborative and Favorite tabs usually fit on one page. For `tab=all`, the table paginates client-side. Either:

- Increase the page-size dropdown to a large value (`100` or `200`) via `javascript_tool`, then re-run the extractor.
- Or click through pages, accumulating `out` across calls.

## 5. Save the list

Write JSON to the working directory so subagents can read it by path:

```
Write /path/to/working_dir/c360/customers.json
[
  {"name": "OpenArt", "cid": "ACC-0000125208", "crmId": "001RC00000ZfhhZYAR"},
  {"name": "Amplifi Pte Ltd", "cid": "ACC-0000264573", "crmId": "001RC00001Meb6zYAB"},
  ...
]
```

## Pitfalls

- **Invisible rows**: virtualized tables only render visible rows. If the count is suspiciously low, scroll the table container to bottom before extracting, or disable virtualization via the page-size dropdown.
- **Duplicate rows**: some tabs merge by account with child rows for products. Dedupe on `crmId` before saving.
- **`CrmAccountId` missing on some rows**: those are group/summary rows. Filter them out (`if (record && record.CrmAccountId)`).
- **Fiber key prefix changes**: React may use `__reactFiber$<random>` — always search by `startsWith('__reactFiber')`, never hardcode.
