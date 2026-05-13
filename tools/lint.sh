#!/usr/bin/env bash
# tools/lint.sh
# Validates all skill manifests in skills/*/ (excluding _template).
# Usage:
#   bash tools/lint.sh              # lint all skills
#   bash tools/lint.sh <skill-name> # lint one skill
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$REPO_DIR/skills"
TEMPLATE="_template"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

errors=0
warnings=0

fail()  { echo -e "${RED}  FAIL${NC}  $*"; errors=$((errors+1)); }
warn()  { echo -e "${YELLOW}  WARN${NC}  $*"; warnings=$((warnings+1)); }
ok()    { echo -e "${GREEN}  OK${NC}    $*"; }

# ── Validate one skill ────────────────────────────────────────────────────────
lint_skill() {
  local skill="$1"
  local dir="$SKILLS_DIR/$skill"
  echo ""
  echo "▸ $skill"

  # Required files
  for f in SKILL.md manifest.yaml CHANGELOG.md "tests/smoke.sh"; do
    if [[ ! -f "$dir/$f" ]]; then
      fail "missing $f"
    else
      ok "$f exists"
    fi
  done

  [[ ! -f "$dir/manifest.yaml" ]] && return  # can't continue without manifest

  # Parse manifest with Python
  python3 - "$dir/manifest.yaml" "$skill" <<'PYEOF'
import sys, yaml, re

path, folder = sys.argv[1], sys.argv[2]
errors = 0

def fail(msg):
    global errors
    print(f"  \033[0;31m  FAIL\033[0m  {msg}")
    errors += 1

def ok(msg):
    print(f"  \033[0;32m  OK\033[0m    {msg}")

with open(path) as f:
    try:
        m = yaml.safe_load(f)
    except yaml.YAMLError as e:
        fail(f"manifest.yaml is not valid YAML: {e}")
        sys.exit(1)

# Required fields
for field in ["name", "version", "stage", "owners", "description_for_install"]:
    if not m.get(field):
        fail(f"manifest.yaml missing required field: {field}")
    else:
        ok(f"{field}: {str(m[field])[:60]}")

# name matches folder
if m.get("name") and m["name"] != folder:
    fail(f"manifest name '{m['name']}' != folder name '{folder}'")

# version is semver
ver = m.get("version", "")
if not re.match(r"^\d+\.\d+\.\d+(-[a-z0-9.-]+)?$", str(ver)):
    fail(f"version '{ver}' is not valid semver (expected X.Y.Z)")

# stage is valid
valid_stages = {"experimental", "beta", "stable", "deprecated"}
stage = m.get("stage", "")
if stage not in valid_stages:
    fail(f"stage '{stage}' must be one of: {sorted(valid_stages)}")

# owners is non-empty list
owners = m.get("owners", [])
if not isinstance(owners, list) or len(owners) == 0:
    fail("owners must be a non-empty list")

# deprecation block required when stage=deprecated
if stage == "deprecated" and not m.get("deprecation"):
    fail("stage=deprecated requires a 'deprecation' block with 'since' and 'remove_after'")

sys.exit(errors)
PYEOF
  # Capture python exit code
  local py_exit=$?
  errors=$((errors + py_exit))

  # smoke.sh must be executable
  if [[ -f "$dir/tests/smoke.sh" ]] && [[ ! -x "$dir/tests/smoke.sh" ]]; then
    warn "tests/smoke.sh is not executable (run: chmod +x $dir/tests/smoke.sh)"
  fi
}

# ── Trigger collision check ───────────────────────────────────────────────────
check_trigger_collisions() {
  echo ""
  echo "▸ Checking trigger collisions across skills..."
  python3 - "$SKILLS_DIR" "$TEMPLATE" <<'PYEOF'
import sys, os, glob, yaml
from collections import defaultdict

skills_dir, template = sys.argv[1], sys.argv[2]
trigger_map = defaultdict(list)

for path in glob.glob(os.path.join(skills_dir, "*/manifest.yaml")):
    skill = os.path.basename(os.path.dirname(path))
    if skill == template:
        continue
    try:
        m = yaml.safe_load(open(path))
        for t in (m.get("triggers") or []):
            trigger_map[t].append(skill)
    except Exception:
        pass

collisions = {t: skills for t, skills in trigger_map.items() if len(skills) > 1}
if collisions:
    for t, skills in collisions.items():
        print(f"  \033[1;33m  WARN\033[0m  Trigger collision '{t}': {skills}")
else:
    print(f"  \033[0;32m  OK\033[0m    No trigger collisions found")
PYEOF
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  if [[ "${1:-}" != "" ]]; then
    # Lint single skill
    lint_skill "$1"
  else
    # Lint all skills except _template
    for dir in "$SKILLS_DIR"/*/; do
      skill=$(basename "$dir")
      [[ "$skill" == "$TEMPLATE" ]] && continue
      lint_skill "$skill"
    done
    check_trigger_collisions
  fi

  echo ""
  if [[ $errors -gt 0 ]]; then
    echo -e "${RED}Lint FAILED — $errors error(s), $warnings warning(s)${NC}"
    exit 1
  elif [[ $warnings -gt 0 ]]; then
    echo -e "${YELLOW}Lint passed with $warnings warning(s)${NC}"
  else
    echo -e "${GREEN}Lint PASSED${NC}"
  fi
}

main "${1:-}"
