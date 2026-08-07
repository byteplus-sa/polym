---
name: polym-byteplus-docs
description: Research BytePlus products, APIs, SDKs, setup, quotas, regions, pricing, and troubleshooting using the bundled official documentation index, then verify claims on live docs. Use for requests for BytePlus documentation or official links.
---

# BytePlus Docs

Research official BytePlus documentation with the bundled `llms.txt` index.
Treat the index as a discovery map of page titles and canonical URLs, never as
evidence for a technical claim. Fetch the relevant live pages before answering.

## Routing boundary

Use this skill for official BytePlus product, API, SDK, setup, quota, region,
pricing, architecture, integration, or troubleshooting documentation.

Do not use it as the primary source for internal SA knowledge, customer context,
Lark discussions, or wiki archival. Use `polym-sa-wiki` for those workflows.
Do not silently substitute Volcengine or third-party documentation when official
BytePlus coverage is missing.

## Prerequisites

- Python 3.10 or later.
- A tool that can fetch live web pages for substantive claim verification.
- Optionally, Context7 library `/websites/byteplus_en` for corroborating current
  API, SDK, or cloud-service details.

Set `SKILL_DIR` to the directory containing this `SKILL.md`. A normal Polym
installation uses:

```bash
SKILL_DIR="${HOME}/.claude/skills/polym-byteplus-docs"
```

The helper finds `llms.txt` beside the skill automatically. Override discovery
only when necessary with `--index PATH` or `BYTEPLUS_LLMS_TXT`.

## Research workflow

1. Extract the product, task, and exact technical nouns from the request.
   Preserve operation names, SDK languages, error codes, and feature names.
2. Search the bundled index with two or three focused query variants. Never load
   the full index into model context.
3. If the product name is uncertain, list the official product sections:

   ```bash
   python3 "${SKILL_DIR}/scripts/search_docs.py" --list-libraries
   ```

4. Decompose mixed requests into separate searches. For a Java backend uploading
   to VOD, search the server-side workflow and the server SDK separately:

   ```bash
   python3 "${SKILL_DIR}/scripts/search_docs.py" \
     "server-side uploads" --library "Video on Demand" --limit 8
   python3 "${SKILL_DIR}/scripts/search_docs.py" \
     "server SDK" --library "Video on Demand" --limit 8
   ```

5. Select the smallest useful source set, normally one overview or guide plus
   one API or SDK reference. Avoid collecting many loosely related pages.
6. Fetch and read those live `docs.byteplus.com` pages. Use Context7 as optional
   corroboration when available, but cite the canonical page from the index.
7. Answer at the user's requested depth. Put the result first, then actionable
   implementation details and limitations when relevant.
8. Cite each important factual claim near the supporting official URL.

For a focused search:

```bash
python3 "${SKILL_DIR}/scripts/search_docs.py" \
  "context caching" --library "ModelArk" --limit 12
python3 "${SKILL_DIR}/scripts/search_docs.py" \
  "custom policy" --library "IAM" --json
```

Prefer exact feature and operation names over generic terms such as `API`,
`guide`, or `overview`.

## Evidence rules

- Distinguish what the index shows (title, product section, URL) from what the
  live page states.
- Verify unstable details at answer time, including pricing, quotas, region
  availability, model lists, SDK versions, endpoints, deprecations, and release
  status.
- Preserve documented prerequisites, regional constraints, authentication
  requirements, and console-versus-API differences.
- For API answers, report operation names, methods or SDK calls, required
  parameters, response fields, and errors only when the selected page supports
  them.
- Keep conflicts visible. Prefer the page with the clearest current or version
  scope instead of silently choosing a result.

## Failure handling

- No matches: remove generic words, try product synonyms, then inspect
  `--list-libraries`.
- Too many matches: add `--library` and search the exact feature or operation.
- Live page unavailable: try the next indexed page covering the same topic.
- Network unavailable: return the most relevant indexed links and state that
  their contents were not live-verified.
- Missing BytePlus coverage: say so and label any adjacent source separately.

## Answer shape

Use only the sections the task needs:

```markdown
[Direct answer with source links near supported claims.]

Implementation notes:
- [Actionable, source-backed detail.]

Limitations or open points:
- [Only when relevant.]
```

For a concise request, prefer one short explanation, three to six actionable
bullets, and two to five official sources.
