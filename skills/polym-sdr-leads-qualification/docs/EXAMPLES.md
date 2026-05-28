# Examples

## Example 1. Score A CSV Directly

User prompt:

`Use the Lead Gen Cortex Operator v1 skill to score this CSV directly and return the qualified, review, and disqualified outputs.`

Preferred execution:

```bash
python3 .claude/skills/polym-sdr-leads-qualification/scripts/score_csv.py \
  --input "/absolute/path/to/trigify.csv" \
  --output-dir "/absolute/path/to/skill-output" \
  --campaign seedance
```

## Example 2. Score Only The First 10 Rows

```bash
python3 .claude/skills/polym-sdr-leads-qualification/scripts/score_csv.py \
  --input "/absolute/path/to/trigify.csv" \
  --output-dir "/absolute/path/to/skill-output" \
  --campaign seedance \
  --limit 10
```

## Example 3. Skip Website Enrichment

```bash
python3 .claude/skills/polym-sdr-leads-qualification/scripts/score_csv.py \
  --input "/absolute/path/to/trigify.csv" \
  --output-dir "/absolute/path/to/skill-output" \
  --campaign seedance \
  --disable-web-enrichment
```

## Example 4. Use A Different Campaign

```bash
python3 .claude/skills/polym-sdr-leads-qualification/scripts/score_csv.py \
  --input "/absolute/path/to/trigify.csv" \
  --output-dir "/absolute/path/to/skill-output" \
  --campaign kling
```

## Example 5. Add A New Campaign

Add a new folder under:

`campaigns/<campaign_id>/`

Required files:

- `config.json`
- `product.md`
- `icp.md`
- `signals.md`
- `disqualification.md`
- `qualification.md`

Then run:

```bash
python3 .claude/skills/polym-sdr-leads-qualification/scripts/score_csv.py \
  --input "/absolute/path/to/trigify.csv" \
  --output-dir "/absolute/path/to/skill-output" \
  --campaign <campaign_id>
```
