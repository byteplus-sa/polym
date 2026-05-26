#!/usr/bin/env bash
# Smoke test for polym-im-digest skill
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "polym-im-digest smoke: checking lark-cli..."
command -v lark-cli >/dev/null || { echo "FAIL: lark-cli not found"; exit 1; }
echo "  OK: lark-cli found"

echo "polym-im-digest smoke: checking reference files..."
for f in references/fetch-workflow.md references/digest-schema.md references/blacklist.md references/product-context.md references/doc-visual-style.md references/codex-routine.md; do
  path="$SKILL_DIR/$f"
  [[ -f "$path" ]] || { echo "FAIL: missing $f"; exit 1; }
  echo "  OK: $f"
done

echo "polym-im-digest smoke: checking blacklist references..."
grep -q "polym-im-digest-blacklist.json" "$SKILL_DIR/SKILL.md" \
  || { echo "FAIL: SKILL.md missing blacklist path"; exit 1; }
grep -q "polym-im-digest-blacklist.json" "$SKILL_DIR/references/fetch-workflow.md" \
  || { echo "FAIL: fetch-workflow.md missing blacklist path"; exit 1; }
echo "  OK: blacklist references"

echo "polym-im-digest smoke: checking priority-first schema..."
grep -q "Priority Queue" "$SKILL_DIR/references/digest-schema.md" \
  || { echo "FAIL: digest schema missing Priority Queue"; exit 1; }
grep -q "Product line" "$SKILL_DIR/references/product-context.md" \
  || { echo "FAIL: product context missing product-line taxonomy"; exit 1; }
grep -q "Do not use .*AIGC Video / Image.* as a product line" "$SKILL_DIR/references/product-context.md" \
  || { echo "FAIL: product context should demote AIGC Video/Image to capability"; exit 1; }
grep -q "Feishu Doc Visual Style" "$SKILL_DIR/references/doc-visual-style.md" \
  || { echo "FAIL: visual style reference missing title"; exit 1; }
grep -q "Content Parity" "$SKILL_DIR/references/doc-visual-style.md" \
  || { echo "FAIL: visual style reference missing content parity rule"; exit 1; }
grep -q "Canonical Layout" "$SKILL_DIR/references/doc-visual-style.md" \
  || { echo "FAIL: visual style reference missing canonical layout"; exit 1; }
grep -q "Content parity is mandatory" "$SKILL_DIR/SKILL.md" \
  || { echo "FAIL: SKILL.md missing content parity rule"; exit 1; }
grep -q "Codex routine" "$SKILL_DIR/references/codex-routine.md" \
  || { echo "FAIL: Codex routine reference missing routine guidance"; exit 1; }
! rg -q "Slack daily digest merge|source: Both|POLYM_IM_DIGEST_MODE=scheduled|scheduled/non-interactive" "$SKILL_DIR/SKILL.md" "$SKILL_DIR/manifest.yaml" "$SKILL_DIR/references" \
  || { echo "FAIL: reverted Slack/scheduled design still referenced"; exit 1; }
echo "  OK: priority-first schema"

echo "polym-im-digest smoke: verifying lark-cli im commands available..."
lark-cli im +messages-search --help >/dev/null 2>&1 \
  || { echo "FAIL: lark-cli im +messages-search not available"; exit 1; }
echo "  OK: +messages-search"

lark-cli im chats list --help >/dev/null 2>&1 \
  || { echo "FAIL: lark-cli im chats list not available"; exit 1; }
echo "  OK: im chats list"

lark-cli im +chat-messages-list --help >/dev/null 2>&1 \
  || { echo "FAIL: lark-cli im +chat-messages-list not available"; exit 1; }
echo "  OK: +chat-messages-list"

lark-cli docs +create --api-version v2 --help >/dev/null 2>&1 \
  || { echo "FAIL: lark-cli docs +create --api-version v2 not available"; exit 1; }
echo "  OK: docs +create v2"

grep -q -- '--content @' "$SKILL_DIR/SKILL.md" \
  || { echo "FAIL: SKILL.md docs create command should use --content @file"; exit 1; }
grep -q -- '--doc-format xml' "$SKILL_DIR/SKILL.md" \
  || { echo "FAIL: SKILL.md docs create command should set --doc-format xml by default"; exit 1; }
grep -q -- '--doc-format markdown' "$SKILL_DIR/SKILL.md" \
  || { echo "FAIL: SKILL.md docs create command should keep markdown fallback"; exit 1; }
grep -q "DIGEST_XML" "$SKILL_DIR/SKILL.md" \
  || { echo "FAIL: SKILL.md should define DIGEST_XML visual output"; exit 1; }
echo "  OK: docs create command"

echo "polym-im-digest smoke: PASS"
