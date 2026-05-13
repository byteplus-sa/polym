#!/usr/bin/env bash
# Smoke test for supper-customer-brief skill
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "supper-customer-brief smoke: checking lark-cli..."
command -v lark-cli >/dev/null || { echo "FAIL: lark-cli not found"; exit 1; }

echo "supper-customer-brief smoke: checking supper-sa-wiki skill..."
SA_WIKI="${HOME}/.claude/skills/supper-sa-wiki/SKILL.md"
[[ -f "$SA_WIKI" ]] || { echo "FAIL: supper-sa-wiki skill not installed at $SA_WIKI"; exit 1; }
echo "  OK: supper-sa-wiki skill found"

echo "supper-customer-brief smoke: checking reference files..."
[[ -f "$SKILL_DIR/references/query-strategy.md" ]] \
  || { echo "FAIL: missing query-strategy.md"; exit 1; }
echo "  OK: query-strategy.md"

echo "supper-customer-brief smoke: PASS"
