#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$SKILL_DIR/scripts/db_path.py" >/dev/null
python3 "$SKILL_DIR/scripts/query.py" --help >/dev/null
python3 "$SKILL_DIR/scripts/query_video.py" --help >/dev/null
echo "polym-eval-db smoke: PASS"
