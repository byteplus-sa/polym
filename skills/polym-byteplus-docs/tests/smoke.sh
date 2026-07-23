#!/usr/bin/env bash
# Offline smoke test for polym-byteplus-docs. Must complete in under 60 seconds.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for required in manifest.yaml SKILL.md CHANGELOG.md llms.txt scripts/search_docs.py; do
  test -f "${SKILL_DIR}/${required}"
done

grep -q "^name: polym-byteplus-docs$" "${SKILL_DIR}/manifest.yaml"
grep -q "^name: polym-byteplus-docs$" "${SKILL_DIR}/SKILL.md"

python3 -c "import ast; ast.parse(open('${SKILL_DIR}/scripts/search_docs.py', encoding='utf-8').read())"
python3 "${SKILL_DIR}/scripts/search_docs.py" --help > /dev/null

LIBRARIES="$(python3 "${SKILL_DIR}/scripts/search_docs.py" --list-libraries)"
grep -q "ModelArk" <<< "${LIBRARIES}"
grep -q "Video on Demand" <<< "${LIBRARIES}"
grep -q "Management Console — IAM" <<< "${LIBRARIES}"

python3 -m unittest discover \
  -s "${SKILL_DIR}/tests" \
  -p "test_*.py"

echo "smoke: ok"
