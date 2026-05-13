#!/usr/bin/env bash
# Smoke test for supper-sa-wiki skill
# Verifies lark-cli is available and the Bitable constants are reachable.
set -euo pipefail

BASE_TOKEN="UXPdbPJ3kaheZvs2Nc8lLGCcglh"
KI_TABLE="tblLKeA8N3ipyEQv"

echo "supper-sa-wiki smoke: checking lark-cli..."
command -v lark-cli >/dev/null || { echo "FAIL: lark-cli not found"; exit 1; }

echo "supper-sa-wiki smoke: querying knowledge_index (limit 1)..."
lark-cli base +record-list \
  --base-token "$BASE_TOKEN" \
  --table-id "$KI_TABLE" \
  --limit 1 \
  --format json \
  --as user >/dev/null

echo "supper-sa-wiki smoke: PASS"
