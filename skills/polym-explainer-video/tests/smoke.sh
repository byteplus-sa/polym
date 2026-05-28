#!/usr/bin/env bash
# Smoke test for polym-explainer-video.
# Must exit 0 on success, non-zero on failure. < 60s. No live secrets.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "polym-explainer-video smoke: manifest exists"
test -f "${SKILL_DIR}/manifest.yaml"

echo "polym-explainer-video smoke: SKILL.md frontmatter exists"
test -f "${SKILL_DIR}/SKILL.md"
grep -q "^name: polym-explainer-video$" "${SKILL_DIR}/SKILL.md"

echo "polym-explainer-video smoke: reference docs and scripts present"
test -f "${SKILL_DIR}/references/storyboard-format.md"
test -f "${SKILL_DIR}/scripts/verify.py"
test -f "${SKILL_DIR}/scripts/compose_and_render.py"
test -f "${SKILL_DIR}/scripts/preflight.py"

echo "polym-explainer-video smoke: PASS"
