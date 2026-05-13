#!/usr/bin/env bash
# SA Super Skill Pack — one-liner installer
#
# ── Ways to install (pick whichever works for you) ────────────────────────────
#
# Option A — gh CLI (recommended, requires gh auth login once):
#   gh repo clone Carey8175/sa-super-skill /tmp/sa-super-skill \
#     && /tmp/sa-super-skill/install.sh
#
# Option B — SSH (if you have an SSH key on GitHub):
#   git clone git@github.com:Carey8175/sa-super-skill.git /tmp/sa-super-skill \
#     && /tmp/sa-super-skill/install.sh
#
# Option C — GitHub Personal Access Token (no special CLI needed):
#   GITHUB_TOKEN=ghp_xxxx bash <(curl -fsSL \
#     -H "Authorization: token ghp_xxxx" \
#     https://raw.githubusercontent.com/Carey8175/sa-super-skill/main/install.sh)
#
# Option D — from inside a cloned repo:
#   ./install.sh [--profile sa-mvp]
#
# Get a token at: https://github.com/settings/tokens (repo:read scope is enough)
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

REPO="Carey8175/sa-super-skill"
DEFAULT_CLONE_DIR="$HOME/.local/share/sa-super-skill"
BIN_DIR="$HOME/.local/bin"
PROFILE="${SA_SUPER_SKILL_PROFILE:-}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

BOLD='\033[1m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

banner() {
  echo ""
  echo -e "${BOLD}╔══════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}║   SA Native AI · Super Skill Pack        ║${NC}"
  echo -e "${BOLD}╚══════════════════════════════════════════╝${NC}"
  echo ""
}

step()  { echo -e "${BLUE}==>${NC} ${BOLD}$*${NC}"; }
ok()    { echo -e "${GREEN} ✓${NC} $*"; }
warn()  { echo -e "${YELLOW} !${NC} $*"; }
die()   { echo -e "${RED} ✗${NC} $*" >&2; exit 1; }

# ── Parse args ────────────────────────────────────────────────────────────────

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --profile) PROFILE="${2:-}"; shift 2 ;;
      --profile=*) PROFILE="${1#--profile=}"; shift ;;
      --token) GITHUB_TOKEN="${2:-}"; shift 2 ;;
      --token=*) GITHUB_TOKEN="${1#--token=}"; shift ;;
      --help|-h)
        echo "Usage: $0 [--profile <name>] [--token <github-pat>]"
        echo ""
        echo "  --profile <name>    Install a specific profile (default: install all)"
        echo "  --token <pat>       GitHub Personal Access Token (for private repo access)"
        echo ""
        echo "Environment:"
        echo "  SA_SUPER_SKILL_PROFILE   Same as --profile"
        echo "  SA_SUPER_SKILL_DIR       Override clone directory"
        echo "  GITHUB_TOKEN             Same as --token"
        echo ""
        echo "Get a token at: https://github.com/settings/tokens (repo:read scope)"
        exit 0 ;;
      *) die "Unknown argument: $1" ;;
    esac
  done
}

# ── Prerequisite checks ───────────────────────────────────────────────────────

check_prereqs() {
  step "Checking prerequisites"
  for dep in git python3; do
    command -v "$dep" &>/dev/null || die "'$dep' is required but not found. Please install it first."
    ok "$dep found"
  done
  echo ""
}

# ── Acquire repo ──────────────────────────────────────────────────────────────

acquire_repo() {
  # If we're already running from inside a cloned repo, use it directly
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -f "$script_dir/registry.yaml" ]]; then
    REPO_DIR="$script_dir"
    ok "Using local repo at $REPO_DIR"
    return
  fi

  REPO_DIR="${SA_SUPER_SKILL_DIR:-$DEFAULT_CLONE_DIR}"
  step "Acquiring repo → $REPO_DIR"

  if [[ -d "$REPO_DIR/.git" ]]; then
    ok "Repo already cloned — pulling latest"
    git -C "$REPO_DIR" pull --ff-only --quiet
    return
  fi

  mkdir -p "$(dirname "$REPO_DIR")"

  # Priority: gh CLI > SSH > GITHUB_TOKEN > HTTPS (prompts for credentials)
  if command -v gh &>/dev/null && gh auth status &>/dev/null 2>&1; then
    ok "Cloning via gh CLI"
    gh repo clone "$REPO" "$REPO_DIR" -- --quiet

  elif [[ -n "$GITHUB_TOKEN" ]]; then
    ok "Cloning via GitHub token"
    git clone --quiet \
      "https://${GITHUB_TOKEN}@github.com/${REPO}.git" "$REPO_DIR"

  elif ssh -T git@github.com &>/dev/null 2>&1 || [[ $? -eq 1 ]]; then
    ok "Cloning via SSH"
    git clone --quiet "git@github.com:${REPO}.git" "$REPO_DIR"

  else
    warn "No gh CLI, SSH key, or GITHUB_TOKEN found."
    warn "Trying HTTPS — you may be prompted for GitHub credentials."
    warn "Tip: set GITHUB_TOKEN=<your-pat> to avoid the prompt."
    echo ""
    git clone "https://github.com/${REPO}.git" "$REPO_DIR" \
      || die "Clone failed. See install options: $0 --help"
  fi
  echo ""
}

# ── Install CLI ───────────────────────────────────────────────────────────────

install_cli() {
  step "Installing super-skill CLI → $BIN_DIR"
  mkdir -p "$BIN_DIR"
  chmod +x "$REPO_DIR/cli/super-skill"
  ln -sf "$REPO_DIR/cli/super-skill" "$BIN_DIR/super-skill"
  ok "super-skill linked at $BIN_DIR/super-skill"
  echo ""
}

# ── PATH hint ─────────────────────────────────────────────────────────────────

maybe_warn_path() {
  if ! echo ":${PATH}:" | grep -q ":${BIN_DIR}:"; then
    warn "$BIN_DIR is not in your PATH."
    echo "   Add this to your ~/.zshrc or ~/.bashrc:"
    echo ""
    echo "     export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
  fi
}

# ── Install skills ────────────────────────────────────────────────────────────

install_skills() {
  step "Installing skills"
  local super_skill="$REPO_DIR/cli/super-skill"

  if [[ -n "$PROFILE" ]]; then
    ok "Mode: profile '$PROFILE'"
    "$super_skill" install "profile:$PROFILE"
  else
    ok "Mode: install all"
    "$super_skill" install all
  fi
}

# ── Main ──────────────────────────────────────────────────────────────────────

main() {
  parse_args "$@"
  banner
  check_prereqs
  acquire_repo
  install_cli
  install_skills
  maybe_warn_path

  echo ""
  echo -e "${GREEN}${BOLD}Setup complete!${NC}"
  echo ""
  echo "  super-skill list              # see what's installed"
  echo "  super-skill doctor            # verify dependencies"
  echo "  super-skill update            # update CLI + installed skills"
  echo ""
}

main "$@"
