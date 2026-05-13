#!/usr/bin/env bash
# Smoke test for meeting-summary skill
set -euo pipefail

echo "meeting-summary smoke: checking lark-cli..."
command -v lark-cli >/dev/null || { echo "FAIL: lark-cli not found"; exit 1; }

echo "meeting-summary smoke: checking vc and minutes commands..."
lark-cli vc --help    >/dev/null 2>&1 || { echo "FAIL: lark-cli vc not available"; exit 1; }
lark-cli minutes --help >/dev/null 2>&1 || { echo "FAIL: lark-cli minutes not available"; exit 1; }

echo "meeting-summary smoke: checking reference files..."
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$SKILL_DIR/references/meeting-fetch.md" ]] || { echo "FAIL: missing meeting-fetch.md"; exit 1; }

echo "meeting-summary smoke: PASS"
