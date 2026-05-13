#!/usr/bin/env bash
# Smoke test for im-digest skill
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "im-digest smoke: checking lark-cli..."
command -v lark-cli >/dev/null || { echo "FAIL: lark-cli not found"; exit 1; }
ok "lark-cli found"

echo "im-digest smoke: checking reference files..."
for f in references/fetch-workflow.md references/digest-schema.md; do
  path="$SKILL_DIR/$f"
  [[ -f "$path" ]] || { echo "FAIL: missing $f"; exit 1; }
  echo "  OK: $f"
done

echo "im-digest smoke: verifying lark-cli im commands available..."
lark-cli im +chat-messages-list --help >/dev/null 2>&1 \
  || { echo "FAIL: lark-cli im +chat-messages-list not available"; exit 1; }
echo "  OK: +chat-messages-list"

echo "im-digest smoke: PASS"
