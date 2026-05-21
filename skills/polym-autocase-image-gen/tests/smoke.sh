#!/usr/bin/env bash
# Smoke test for polym-autocase-image-gen.
# Skill has no CLI surface — it runs entirely via Claude in Chrome MCP tools.
# So this test only validates static artifacts.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# 1. manifest exists
test -f "${SKILL_DIR}/manifest.yaml"

# 2. SKILL.md exists and has frontmatter
grep -q "^---$" "${SKILL_DIR}/SKILL.md"

# 3. CHANGELOG exists
test -f "${SKILL_DIR}/CHANGELOG.md"

# 4. SKILL.md frontmatter name matches the folder
grep -q "^name: polym-autocase-image-gen$" "${SKILL_DIR}/SKILL.md"

# 5. manifest name matches folder
grep -q "^name: polym-autocase-image-gen$" "${SKILL_DIR}/manifest.yaml"

echo "smoke: ok"
