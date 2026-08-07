#!/usr/bin/env bash
# Smoke test for polym-bp-cloud.
# Must exit 0 on success, non-zero on failure. < 60s. No live secrets.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# 1. manifest parses
test -f "${SKILL_DIR}/manifest.yaml"

# 2. SKILL.md exists and has frontmatter
grep -q "^---$" "${SKILL_DIR}/SKILL.md"

# 3. reference files present
for f in provision-ecs cloud-assistant tos; do
  test -f "${SKILL_DIR}/references/${f}.md"
done

# 4. ve CLI present and responds (no credentials needed for these)
ve version > /dev/null
ve ecs --help | grep -q RunInstances
ve ecs --help | grep -q DescribeCloudAssistantStatus
ve vpc --help | grep -q DescribeVpcs

echo "smoke: ok"
