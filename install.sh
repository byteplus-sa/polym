#!/usr/bin/env bash
# Polym — one-liner installer
#
# ── Ways to install (pick whichever works for you) ────────────────────────────
#
# Option A — gh CLI (recommended, requires gh auth login once):
#   gh repo clone byteplus-sa/polym /tmp/polym \
#     && /tmp/polym/install.sh
#
# Option B — SSH (if you have an SSH key on GitHub):
#   git clone git@github.com:byteplus-sa/polym.git /tmp/polym \
#     && /tmp/polym/install.sh
#
# Option C — GitHub Personal Access Token (no special CLI needed):
#   GITHUB_TOKEN=ghp_xxxx bash <(curl -fsSL \
#     -H "Authorization: token ghp_xxxx" \
#     https://raw.githubusercontent.com/byteplus-sa/polym/main/install.sh)
#
# Option D — from inside a cloned repo:
#   ./install.sh [--profile sa-mvp]
#
# Get a token at: https://github.com/settings/tokens (repo:read scope is enough)
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

REPO="byteplus-sa/polym"
DEFAULT_CLONE_DIR="$HOME/.local/share/polym"
BIN_DIR="$HOME/.local/bin"
PROFILE="${POLYM_PROFILE:-}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

BOLD='\033[1m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

banner() {
  echo ""
  echo -e "${BOLD}╔══════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}║   Polym · SA Native AI Skill Pack     ║${NC}"
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
        echo "  POLYM_PROFILE   Same as --profile"
        echo "  POLYM_DIR       Override clone directory"
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

  REPO_DIR="${POLYM_DIR:-$DEFAULT_CLONE_DIR}"
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
  step "Installing polym CLI → $BIN_DIR"
  mkdir -p "$BIN_DIR"
  chmod +x "$REPO_DIR/cli/polym"
  ln -sf "$REPO_DIR/cli/polym" "$BIN_DIR/polym"
  ok "polym linked at $BIN_DIR/polym"
  echo ""
}

# ── PATH hint ─────────────────────────────────────────────────────────────────

maybe_warn_path() {
  if ! echo ":${PATH}:" | grep -q ":${BIN_DIR}:"; then
    warn "$BIN_DIR is not in your PATH."
    echo "   Add it to your shell startup file:"
    echo ""
    echo "     # zsh:"
    echo "     echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc"
    echo ""
    echo "     # bash on macOS:"
    echo "     echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bash_profile && source ~/.bash_profile"
    echo ""
  fi
}

# ── Install skills ────────────────────────────────────────────────────────────

install_skills() {
  step "Installing skills"
  local polym="$REPO_DIR/cli/polym"

  if [[ -n "$PROFILE" ]]; then
    ok "Mode: profile '$PROFILE'"
    "$polym" install "profile:$PROFILE"
  else
    ok "Mode: install all"
    "$polym" install all
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
  echo "  polym list              # see what's installed"
  echo "  polym doctor            # verify dependencies"
  echo "  polym update            # update CLI + installed skills"
  echo ""
}

main "$@"
