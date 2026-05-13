#!/usr/bin/env bash
# Smoke test for TEMPLATE-RENAME-ME.
# Must exit 0 on success, non-zero on failure. < 60s. No live secrets.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# 1. manifest parses
test -f "${SKILL_DIR}/manifest.yaml"

# 2. SKILL.md exists and has frontmatter
grep -q "^---$" "${SKILL_DIR}/SKILL.md"

# 3. primary CLI surface responds (replace with your real check)
# lark-cli your-command --help > /dev/null

echo "smoke: ok"
