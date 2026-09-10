#!/usr/bin/env bash
# Offline smoke test for polym-byteplus-ppt-creator. Must complete in under 60 seconds.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for required in manifest.yaml SKILL.md CHANGELOG.md; do
  test -f "${SKILL_DIR}/${required}"
done

grep -q "^name: polym-byteplus-ppt-creator$" "${SKILL_DIR}/manifest.yaml"
grep -q "^name: polym-byteplus-ppt-creator$" "${SKILL_DIR}/SKILL.md"

# Validator script parses and responds to --help
python3 -c "import ast; ast.parse(open('${SKILL_DIR}/scripts/validate_byteplus_pptx.py', encoding='utf-8').read())"
python3 "${SKILL_DIR}/scripts/validate_byteplus_pptx.py" --help > /dev/null

# Template asset present
test -f "${SKILL_DIR}/assets/BytePlus Presentation Template_FEB 2026.pptx"

# Catalog exists and is valid JSON
python3 -c "import json; json.load(open('${SKILL_DIR}/references/template-slide-catalog.json', encoding='utf-8'))"

# Unit tests
python3 -m unittest discover \
  -s "${SKILL_DIR}/tests" \
  -p "test_*.py"

echo "smoke: ok"
