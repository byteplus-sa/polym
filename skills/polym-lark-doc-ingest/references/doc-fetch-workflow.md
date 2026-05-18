# Document Fetch Workflow

## Discovery Commands

```bash
# Documents edited since yesterday
lark-cli drive +search --query "" \
  --edited-since "$(date -v-1d +%Y-%m-%d)" \
  --doc-types docx \
  --page-size 20 --format json --as user

# Documents created since yesterday
lark-cli drive +search --query "" \
  --created-since "$(date -v-1d +%Y-%m-%d)" \
  --doc-types docx \
  --page-size 20 --format json --as user

# With folder filter
lark-cli drive +search --query "" \
  --edited-since "$(date -v-1d +%Y-%m-%d)" \
  --doc-types docx \
  --folder-tokens <fld_xxx> \
  --page-size 20 --format json --as user
```

## Search Response Fields

Key fields from `drive +search` response:

```json
{
  "items": [
    {
      "token": "SMRKdLOO0oBDgNxIoNZlvJ8WgUg",  // doc token
      "name": "Acme POC 评估报告",               // title
      "type": "docx",
      "url": "https://bytedance.sg.larkoffice.com/docx/SMRKd...",
      "owner_id": "ou_xxx",
      "create_time": "1715000000",               // unix timestamp
      "edit_time": "1715100000"
    }
  ],
  "page_token": "...",
  "has_more": false
}
```

## Fetch Strategies

### Strategy A: Outline first (recommended for batch)

```bash
# Step 1: Get outline (cheap — returns heading structure only)
lark-cli docs +fetch --api-version v2 \
  --doc <token> --scope outline --as user

# Step 2: Decide if worth full fetch based on outline
# Step 3: Get full content only if classified as relevant
lark-cli docs +fetch --api-version v2 \
  --doc <token> --format pretty --as user
```

### Strategy B: Section-targeted fetch

For long documents, fetch only relevant sections:

```bash
# Fetch by keyword (finds sections containing the keyword)
lark-cli docs +fetch --api-version v2 \
  --doc <token> --scope keyword --keyword "客户" --as user

# Fetch a specific section by heading text
lark-cli docs +fetch --api-version v2 \
  --doc <token> --scope section --start-block-id <block_id> --as user
```

## Duplicate Detection

Check if a document was already ingested by looking for its token in local wiki:

```bash
grep -rl "^doc_id: <token>" \
  $LOCAL_WIKI_ROOT/wiki/sources/ 2>/dev/null
```

If any file is found, document is already ingested — skip.

Also check Lark wiki via polym-sa-wiki knowledge_index:

```bash
lark-cli base +record-search \
  --base-token UXPdbPJ3kaheZvs2Nc8lLGCcglh \
  --table-id tblLKeA8N3ipyEQv \
  --json '{"filter":{"conjunction":"and","conditions":[
    {"field_name":"doc_token","operator":"is","value":["<token>"]}
  ]}}' --format json --as user
```

## URL Cleanup

When storing the doc URL in wiki frontmatter, always strip disposable_login_token:

```python
import re
clean_url = re.sub(r'[?&]disposable_login_token=[^&]*', '', url)
clean_url = re.sub(r'[?&]dcuId=[^&]*', '', clean_url)
clean_url = re.sub(r'[?&]from=[^&]*', '', clean_url)
# Remove trailing ? or &
clean_url = re.sub(r'[?&]$', '', clean_url)
# Remove fragment
clean_url = clean_url.split('#')[0]
```

## Slug Generation

Generate filename slug from document title:

```python
import re
def to_slug(title):
    # Lowercase
    slug = title.lower()
    # Replace Chinese/special chars with hyphens
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    # Truncate to 50 chars
    return slug[:50]
```

## Error Handling

| Error | Action |
|---|---|
| `403` on doc fetch | Skip silently, note `[无权限]` in report |
| `404` on doc fetch | Skip, note `[文档不存在或已删除]` |
| Doc too large (>100KB) | Fetch outline + first 3 sections only |
| `drive +search` rate limit | Wait 2 seconds, retry once |
| Pagination (has_more=true) | Fetch up to 3 pages max (60 docs) — warn if more |

## Parallel Processing

Process docs in batches of up to 5 in parallel.

For each batch:
1. Launch 5 outline-fetch agents in one message
2. Wait for all to return
3. Classify and decide which need full fetch
4. Launch full-fetch agents for qualifying docs (in parallel)
5. Write results to wiki

This keeps total latency reasonable even for 20+ docs.
