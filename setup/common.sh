# Shared helpers for platform setup scripts (mac-setup.sh, wsl-setup.sh).
# Source from the dotfiles repo root:
#   source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/setup/common.sh"

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

log_info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

command_exists() {
  command -v "$1" &>/dev/null
}

safe_source() {
  if [[ -f "$1" ]]; then
    # shellcheck disable=SC1090
    source "$1"
    return 0
  fi
  return 1
}

run_safe() {
  set +e
  "$@" >/dev/null 2>&1
  local exit_code=$?
  set -e
  return "$exit_code"
}

get_git_config() {
  git config --get "$1" 2>/dev/null || echo ""
}

prompt_for_git_identity() {
  if [[ -z "${GIT_EMAIL:-}" ]]; then
    GIT_EMAIL="$(get_git_config user.email)"
    if [[ -z "$GIT_EMAIL" ]]; then
      echo -n "Enter your Git email: "
      read -r GIT_EMAIL
    else
      log_info "Using Git email from config: $GIT_EMAIL"
    fi
    export GIT_EMAIL
  fi

  if [[ -z "${FULL_NAME:-}" ]]; then
    FULL_NAME="$(get_git_config user.name)"
    if [[ -z "$FULL_NAME" ]]; then
      echo -n "Enter your full name: "
      read -r FULL_NAME
    else
      log_info "Using Git name from config: $FULL_NAME"
    fi
    export FULL_NAME
  fi
}

dotfiles_repo_dir() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
  if [[ -f "${script_dir}/rcrc" ]]; then
    printf '%s\n' "$script_dir"
    return 0
  fi
  if [[ -d "${HOME}/dotfiles" && -f "${HOME}/dotfiles/rcrc" ]]; then
    printf '%s\n' "${HOME}/dotfiles"
    return 0
  fi
  return 1
}

ensure_dotfiles_local_gitconfig() {
  local gitconfig_local="${HOME}/dotfiles-local/gitconfig.local"
  mkdir -p "${HOME}/dotfiles-local"

  if [[ -f "$gitconfig_local" ]]; then
    log_info "Keeping existing ${gitconfig_local}"
    return 0
  fi

  prompt_for_git_identity

  cat >"$gitconfig_local" <<EOF
[user]
  name = ${FULL_NAME}
  email = ${GIT_EMAIL}
EOF
  log_info "Wrote ${gitconfig_local}"
}

run_rcup() {
  local dotfiles_dir="$1"
  if ! command_exists rcup; then
    log_error "rcup not found. Install rcm (macOS: brew install rcm; Ubuntu: sudo apt install rcm)."
    return 1
  fi

  log_info "Running rcup from ${dotfiles_dir}..."
  env RCRC="${dotfiles_dir}/rcrc" rcup
}

run_sync_ai_assistants() {
  local dotfiles_dir="$1"
  local sync="${dotfiles_dir}/bin/sync-ai-assistants"
  if [[ ! -x "$sync" ]]; then
    log_warn "sync-ai-assistants not found at ${sync}; skipping"
    return 0
  fi

  log_info "Syncing Claude/Cursor harness..."
  DOTFILES_DIR="$dotfiles_dir" "$sync"
  DOTFILES_DIR="$dotfiles_dir" "$sync" --verify
}
