#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
grep -q "name: polym-eval-seed-llm-gtm" "$SKILL_DIR/SKILL.md"
echo "polym-eval-seed-llm-gtm smoke: PASS"
