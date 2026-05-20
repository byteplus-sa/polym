#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
grep -q "name: polym-eval-seedance-aigc-gtm" "$SKILL_DIR/SKILL.md"
echo "polym-eval-seedance-aigc-gtm smoke: PASS"
