#!/usr/bin/env bash
# Smoke test for polymath-help skill
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "polymath-help smoke: checking SKILL.md sections..."
for section in "Section 1" "Section 2" "Section 3" "Section 4" "Quick Reference"; do
  grep -q "$section" "$SKILL_DIR/SKILL.md" \
    || { echo "FAIL: missing '$section' in SKILL.md"; exit 1; }
  echo "  OK: $section found"
done

echo "polymath-help smoke: PASS"
