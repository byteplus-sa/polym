#!/usr/bin/env bash
# Smoke test for polym-customer-brief skill
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "polym-customer-brief smoke: checking lark-cli..."
command -v lark-cli >/dev/null || { echo "FAIL: lark-cli not found"; exit 1; }

echo "polym-customer-brief smoke: checking polym-sa-wiki skill..."
SA_WIKI="${HOME}/.claude/skills/polym-sa-wiki/SKILL.md"
[[ -f "$SA_WIKI" ]] || { echo "FAIL: polym-sa-wiki skill not installed at $SA_WIKI"; exit 1; }
echo "  OK: polym-sa-wiki skill found"

echo "polym-customer-brief smoke: checking reference files..."
[[ -f "$SKILL_DIR/references/query-strategy.md" ]] \
  || { echo "FAIL: missing query-strategy.md"; exit 1; }
echo "  OK: query-strategy.md"

echo "polym-customer-brief smoke: PASS"
