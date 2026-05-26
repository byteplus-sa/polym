#!/usr/bin/env bash
# Smoke test: verify required scripts are present and importable
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== polym-slack-digest smoke test ==="

# Verify required scripts exist
required_scripts=(
  "scripts/platform.py"
  "scripts/save_credentials.py"
  "scripts/list_channels.py"
  "scripts/pull_history.py"
  "scripts/build_digest.py"
  "scripts/run_digest.py"
  "scripts/lark_doc_client.py"
  "scripts/local_routine.py"
  "scripts/watchdog.py"
  "scripts/notify_lark.py"
)

for script in "${required_scripts[@]}"; do
  if [[ ! -f "$SKILL_DIR/$script" ]]; then
    echo "FAIL: missing $script"
    exit 1
  fi
done

# Verify Python syntax on each script
for script in "${required_scripts[@]}"; do
  python3 -m py_compile "$SKILL_DIR/$script" || { echo "FAIL: syntax error in $script"; exit 1; }
done

echo "PASS: all required scripts present and syntax-valid"
exit 0
