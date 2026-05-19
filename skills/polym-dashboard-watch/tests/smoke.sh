#!/usr/bin/env bash
# Smoke test for polym-dashboard-watch skill
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "polym-dashboard-watch smoke: checking reference files..."
for f in c360-query.md customer-list-extraction.md customer-usage-query.md subagent-prompt-template.md; do
  [[ -f "$SKILL_DIR/references/$f" ]] || { echo "FAIL: missing references/$f"; exit 1; }
  echo "  OK: references/$f"
done

echo "polym-dashboard-watch smoke: PASS"
