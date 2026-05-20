#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if ! output="$(python3 "$SKILL_DIR/scripts/generate.py" --help 2>&1 >/dev/null)"; then
  if [[ "$output" == *"ModuleNotFoundError: No module named"* ]]; then
    echo "polym-eval-generate-gemini smoke: SKIP ($output)"
    exit 0
  fi
  echo "$output" >&2
  exit 1
fi
echo "polym-eval-generate-gemini smoke: PASS"
