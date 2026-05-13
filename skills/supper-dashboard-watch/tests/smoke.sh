#!/usr/bin/env bash
# Smoke test for supper-dashboard-watch skill
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "supper-dashboard-watch smoke: checking reference files..."
[[ -f "$SKILL_DIR/references/c360-query.md" ]] || { echo "FAIL: missing c360-query.md"; exit 1; }
echo "  OK: c360-query.md"

echo "supper-dashboard-watch smoke: checking c360-customer-usage skill exists..."
C360_SKILL="${HOME}/.claude/skills/c360-customer-usage/SKILL.md"
if [[ ! -f "$C360_SKILL" ]]; then
  echo "  WARN: c360-customer-usage skill not installed at $C360_SKILL"
  echo "  Install with: super-skill install c360-customer-usage (when available)"
else
  echo "  OK: c360-customer-usage skill found"
fi

echo "supper-dashboard-watch smoke: PASS"
