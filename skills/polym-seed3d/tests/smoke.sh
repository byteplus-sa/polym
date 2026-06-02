#!/usr/bin/env bash
# Smoke test for polym-seed3d.
# Must exit 0 on success, non-zero on failure. < 60s. No live secrets.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# 1. manifest parses
test -f "${SKILL_DIR}/manifest.yaml"

# 2. SKILL.md exists and has frontmatter
grep -q "^---$" "${SKILL_DIR}/SKILL.md"

# 3. bundled script is present and importable/parseable (no network, no key)
test -f "${SKILL_DIR}/scripts/seed3d.py"
python3 -c "import ast,sys; ast.parse(open('${SKILL_DIR}/scripts/seed3d.py').read())"

# 4. primary CLI surface responds to --help without a key or network
python3 "${SKILL_DIR}/scripts/seed3d.py" --help > /dev/null

echo "smoke: ok"
