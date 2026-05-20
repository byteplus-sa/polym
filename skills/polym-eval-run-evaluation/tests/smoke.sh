#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$SKILL_DIR/scripts/save_to_db.py" --help >/dev/null
echo "polym-eval-run-evaluation smoke: PASS"
