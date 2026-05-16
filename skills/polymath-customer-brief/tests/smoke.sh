#!/usr/bin/env bash
# Smoke test for polymath-customer-brief skill
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "polymath-customer-brief smoke: checking lark-cli..."
command -v lark-cli >/dev/null || { echo "FAIL: lark-cli not found"; exit 1; }

echo "polymath-customer-brief smoke: checking polymath-sa-wiki skill..."
SA_WIKI="${HOME}/.claude/skills/polymath-sa-wiki/SKILL.md"
[[ -f "$SA_WIKI" ]] || { echo "FAIL: polymath-sa-wiki skill not installed at $SA_WIKI"; exit 1; }
echo "  OK: polymath-sa-wiki skill found"

echo "polymath-customer-brief smoke: checking reference files..."
[[ -f "$SKILL_DIR/references/query-strategy.md" ]] \
  || { echo "FAIL: missing query-strategy.md"; exit 1; }
echo "  OK: query-strategy.md"

echo "polymath-customer-brief smoke: PASS"
