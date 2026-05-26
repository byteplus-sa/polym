#!/usr/bin/env bash
# Smoke test for polym-slack-digest.
# Must exit 0 on success, non-zero on failure. < 60s. No live secrets.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# 1. manifest parses
test -f "${SKILL_DIR}/manifest.yaml"

# 2. SKILL.md exists and has frontmatter
grep -q "^---$" "${SKILL_DIR}/SKILL.md"

# 3. Required scripts are present
for script in save_credentials.py list_channels.py pull_history.py build_digest.py \
              run_digest.py platform.py lark_doc_client.py local_routine.py \
              watchdog.py notify_lark.py; do
  test -f "${SKILL_DIR}/scripts/${script}"
done

# 4. Required references are present
for ref in slack-app-setup.md lark-bot-setup.md digest-template.md; do
  test -f "${SKILL_DIR}/references/${ref}"
done

# 5. Python syntax check on all scripts (no imports executed)
python3 -m py_compile "${SKILL_DIR}"/scripts/*.py

echo "smoke: ok"
