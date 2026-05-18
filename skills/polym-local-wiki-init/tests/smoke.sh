#!/usr/bin/env bash
# Smoke test for polym-local-wiki-init skill
# Verifies the skill's reference templates are present and non-empty.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "polym-local-wiki-init smoke: checking reference templates..."

for f in references/readme-template.md references/schema-template.md references/prompts-template.md; do
  path="$SKILL_DIR/$f"
  [[ -f "$path" ]] || { echo "FAIL: missing $f"; exit 1; }
  [[ -s "$path" ]] || { echo "FAIL: $f is empty"; exit 1; }
  echo "  OK: $f ($(wc -l < "$path") lines)"
done

echo "polym-local-wiki-init smoke: PASS"
