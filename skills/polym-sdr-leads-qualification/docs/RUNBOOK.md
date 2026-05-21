# CSV Runbook

Use this runbook when the user wants the skill package itself to process a CSV file end to end.

## What The Skill Package Can Execute

The skill package includes a standalone script:

`scripts/score_csv.py`

This script:

1. reads a Trigify-style CSV
2. normalizes each lead
3. performs lightweight enrichment
4. makes 1 LLM call per lead (evidence extraction + scoring in one pass)
5. applies deterministic score validation and routing in Python
6. writes scored CSV outputs and JSON artifacts

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `LLM_API_KEY` | Yes | API key for your provider |
| `LLM_MODEL` | Yes | Model name (see examples below) |
| `LLM_PROVIDER` | No | Provider hint — auto-detected from model name if omitted |
| `LLM_API_BASE` | No | Override the API endpoint (required for BytePlus Ark) |

## Provider Examples

### Anthropic (Claude)

```bash
export LLM_API_KEY="sk-ant-..."
export LLM_MODEL="claude-sonnet-4-6"
export LLM_PROVIDER="anthropic"

python3 ~/.claude/skills/polym-sdr-leads-qualification/scripts/score_csv.py \
  --input "/path/to/leads.csv" \
  --output-dir "/path/to/output" \
  --campaign seedance
```

### OpenAI

```bash
export LLM_API_KEY="sk-..."
export LLM_MODEL="gpt-4o"
export LLM_PROVIDER="openai"

python3 ~/.claude/skills/polym-sdr-leads-qualification/scripts/score_csv.py \
  --input "/path/to/leads.csv" \
  --output-dir "/path/to/output" \
  --campaign seedance
```

### Google Gemini

```bash
export LLM_API_KEY="AIza..."
export LLM_MODEL="gemini-2.0-flash"
export LLM_PROVIDER="gemini"

python3 ~/.claude/skills/polym-sdr-leads-qualification/scripts/score_csv.py \
  --input "/path/to/leads.csv" \
  --output-dir "/path/to/output" \
  --campaign seedance
```

### BytePlus Ark

```bash
export LLM_API_KEY="<ark-api-key>"
export LLM_MODEL="ep-<your-endpoint-id>"
export LLM_PROVIDER="openai"
export LLM_API_BASE="https://ark.ap-southeast.bytepluses.com/api/v3"

python3 ~/.claude/skills/polym-sdr-leads-qualification/scripts/score_csv.py \
  --input "/path/to/leads.csv" \
  --output-dir "/path/to/output" \
  --campaign seedance
```

## CLI Flags (override env vars)

```
--provider    LLM provider (anthropic, openai, gemini, …)
--model       Model name
--api-key     API key
--api-base    Override API endpoint
--campaign    Campaign pack to use (seedance or kling, default: seedance)
--limit N     Process only the first N rows
--disable-web-enrichment   Skip website fetch per lead
--sleep-ms N  Pause N ms between leads (rate limit control)
```

## Output Files

```
all_scored_leads.csv
qualified_leads.csv
review_leads.csv
disqualified_leads.csv
summary.json
artifacts/{lead_id}_input.json
artifacts/{lead_id}_enrichment.json
artifacts/{lead_id}_evidence.json
artifacts/{lead_id}_decision.json
```

## Operational Notes

- Website enrichment is best-effort only — failures are silently skipped.
- Routing is always revalidated in Python after the LLM call.
- Hard disqualifiers and low signal strength override the model score.
- Any LiteLLM-compatible provider works — see [LiteLLM docs](https://docs.litellm.ai/docs/providers) for the full list.

## When To Use The Backend Instead

Use the backend only when the user wants:

- persistent memory
- run history
- campaign activation
- email preview/export/send

Do not require the backend when the user only wants:

- CSV scoring
- a scored output file
- per-lead evidence and decision artifacts
