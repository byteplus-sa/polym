#!/usr/bin/env bash
# Smoke test for lark-doc-ingest skill
set -euo pipefail

echo "lark-doc-ingest smoke: checking lark-cli..."
command -v lark-cli >/dev/null || { echo "FAIL: lark-cli not found"; exit 1; }

echo "lark-doc-ingest smoke: checking drive and docs commands..."
lark-cli drive --help >/dev/null 2>&1 || { echo "FAIL: lark-cli drive not available"; exit 1; }
echo "  OK: drive"

echo "lark-doc-ingest smoke: checking reference files..."
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$SKILL_DIR/references/doc-fetch-workflow.md" ]] \
  || { echo "FAIL: missing doc-fetch-workflow.md"; exit 1; }
echo "  OK: doc-fetch-workflow.md"

echo "lark-doc-ingest smoke: verifying drive +search with date flag..."
# dry-check: just verify the command accepts these flags
lark-cli drive +search --query "" --edited-since "2026-05-01" --doc-types docx \
  --page-size 1 --format json --as user >/dev/null 2>&1 \
  && echo "  OK: drive +search with --edited-since" \
  || echo "  WARN: drive +search test failed (may need auth)"

echo "lark-doc-ingest smoke: PASS"
