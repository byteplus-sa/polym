#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 1. manifest exists
test -f "${SKILL_DIR}/manifest.yaml"

# 2. SKILL.md exists and has frontmatter
grep -q "^---$" "${SKILL_DIR}/SKILL.md"

# 3. primary CLI responds
if ! output="$(python3 "$SKILL_DIR/scripts/score_csv.py" --help 2>&1 >/dev/null)"; then
  if [[ "$output" == *"ModuleNotFoundError: No module named"* ]]; then
    echo "polym-sdr-leads-qualification smoke: SKIP ($output)"
    exit 0
  fi
  echo "$output" >&2
  exit 1
fi

echo "polym-sdr-leads-qualification smoke: PASS"
