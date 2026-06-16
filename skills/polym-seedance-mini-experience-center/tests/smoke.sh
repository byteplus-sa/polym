#!/usr/bin/env bash
# Smoke test for polym-seedance-mini-experience-center.
# Must exit 0 on success, non-zero on failure. < 60s. No live secrets / no network.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# 1. required files exist
test -f "${SKILL_DIR}/manifest.yaml"
test -f "${SKILL_DIR}/SKILL.md"
test -f "${SKILL_DIR}/scripts/creds.py"
test -f "${SKILL_DIR}/scripts/mini.py"
test -f "${SKILL_DIR}/scripts/assets.py"

# 2. SKILL.md has frontmatter
grep -q "^---$" "${SKILL_DIR}/SKILL.md"

# 3. scripts compile (syntax check, no import / no network / no secrets)
python3 -m py_compile \
  "${SKILL_DIR}/scripts/creds.py" \
  "${SKILL_DIR}/scripts/mini.py" \
  "${SKILL_DIR}/scripts/assets.py"

# 4. no embedded credentials in the skill tree
if grep -rIlE 'AKLT[A-Za-z0-9]{12}|-----BEGIN|csrfToken"[: ]+"[0-9a-f]{16}' \
     "${SKILL_DIR}" --include='*.py' --include='*.md' --include='*.json' 2>/dev/null; then
  echo "smoke: FAIL — possible embedded secret"; exit 1
fi

echo "smoke: ok"
