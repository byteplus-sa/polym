#!/usr/bin/env bash
set -euo pipefail

skill_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

grep -q "lark-cli calendar +agenda" "$skill_dir/SKILL.md"
grep -q "note_taker__start_session" "$skill_dir/SKILL.md"
grep -q "note_taker__end_session" "$skill_dir/SKILL.md"
grep -q "note_taker__finalize_meeting" "$skill_dir/SKILL.md"
grep -q "supper-sa-wiki" "$skill_dir/SKILL.md"
grep -q "local wiki" "$skill_dir/SKILL.md"
test -f "$skill_dir/references/lark-calendar-kickoff.md"
test -f "$skill_dir/references/finalization-workflow.md"

echo "supper-meeting-recorder smoke: PASS"

