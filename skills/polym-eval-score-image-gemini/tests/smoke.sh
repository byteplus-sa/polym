#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$SKILL_DIR/scripts/evaluate.py" --help >/dev/null
echo "polym-eval-score-image-gemini smoke: PASS"
