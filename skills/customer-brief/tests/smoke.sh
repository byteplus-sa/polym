#!/usr/bin/env bash
# Smoke test for customer-brief skill
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "customer-brief smoke: checking lark-cli..."
command -v lark-cli >/dev/null || { echo "FAIL: lark-cli not found"; exit 1; }

echo "customer-brief smoke: checking sa-wiki skill..."
SA_WIKI="${HOME}/.claude/skills/sa-wiki/SKILL.md"
[[ -f "$SA_WIKI" ]] || { echo "FAIL: sa-wiki skill not installed at $SA_WIKI"; exit 1; }
echo "  OK: sa-wiki skill found"

echo "customer-brief smoke: checking reference files..."
[[ -f "$SKILL_DIR/references/query-strategy.md" ]] \
  || { echo "FAIL: missing query-strategy.md"; exit 1; }
echo "  OK: query-strategy.md"

echo "customer-brief smoke: PASS"
