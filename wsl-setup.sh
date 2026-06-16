#!/usr/bin/env bash
################################################################################
# WSL2 Development Environment Setup Script
#
# Bootstraps Ubuntu on WSL with the dotfiles repo, rcm/rcup, and common CLI tools.
# Run inside WSL after Windows host setup (see windows-setup.ps1).
#
# Usage:
#   ./wsl-setup.sh
#   ./setup.sh          # preferred — auto-routes by platform
#
# Optional environment variables:
#   GIT_EMAIL, FULL_NAME — skip interactive prompts
#   DOTFILES_REPO — override clone URL (default: andrewwylde/dotfiles)
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=setup/common.sh
source "${SCRIPT_DIR}/setup/common.sh"

readonly DOTFILES_REPO="${DOTFILES_REPO:-https://github.com/andrewwylde/dotfiles.git}"
readonly DOTFILES_DIR="${DOTFILES_DIR:-${HOME}/dotfiles}"
readonly PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
readonly NVM_INSTALL_VERSION="${NVM_INSTALL_VERSION:-v0.39.7}"

require_wsl() {
  if [[ "$(uname -s)" != "Linux" ]]; then
    log_error "This script must run inside WSL/Linux (found: $(uname -s))"
    exit 1
  fi

  if grep -qi microsoft /proc/version 2>/dev/null; then
    log_info "Detected WSL: $(head -n1 /proc/version)"
    return 0
  fi

  log_warn "Not running under WSL kernel — continuing on Linux anyway"
}

install_apt_packages() {
  log_info "Installing apt packages..."
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential \
    ca-certificates \
    curl \
    git \
    jq \
    rcm \
    ripgrep \
    unzip \
    wget \
    zsh \
    python3 \
    python3-pip \
    python3-venv \
    postgresql-client \
    openssh-client \
    gnupg \
    software-properties-common
}

install_gh_cli() {
  if command_exists gh; then
    log_info "GitHub CLI already installed"
    return 0
  fi

  log_info "Installing GitHub CLI..."
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
  sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null
  sudo apt-get update
  sudo apt-get install -y gh
}

install_oh_my_zsh() {
  if [[ -d "${HOME}/.oh-my-zsh" ]]; then
    log_info "oh-my-zsh already installed"
    return 0
  fi

  log_info "Installing oh-my-zsh (required by dotfiles zshrc)..."
  RUNZSH=no CHSH=no KEEP_ZSHRC=yes sh -c \
    "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
}

set_default_zsh() {
  local zsh_path
  zsh_path="$(command -v zsh)"
  if [[ -z "$zsh_path" ]]; then
    log_warn "zsh not found; skipping chsh"
    return 0
  fi

  if [[ "${SHELL:-}" == "$zsh_path" ]]; then
    log_info "zsh already default shell"
    return 0
  fi

  if ! grep -qxF "$zsh_path" /etc/shells 2>/dev/null; then
    echo "$zsh_path" | sudo tee -a /etc/shells >/dev/null
  fi

  log_info "Setting default shell to ${zsh_path} (may prompt for password)..."
  chsh -s "$zsh_path" "$USER" || log_warn "chsh failed — run manually: chsh -s ${zsh_path}"
}

clone_dotfiles() {
  if [[ -d "${DOTFILES_DIR}/.git" ]]; then
    log_info "Dotfiles already cloned at ${DOTFILES_DIR}"
    return 0
  fi

  log_info "Cloning dotfiles to ${DOTFILES_DIR}..."
  git clone "${DOTFILES_REPO}" "${DOTFILES_DIR}"
}

install_nvm_and_node() {
  if [[ ! -d "${HOME}/.nvm" ]]; then
    log_info "Installing nvm..."
    curl -o- "https://raw.githubusercontent.com/nvm-sh/nvm/${NVM_INSTALL_VERSION}/install.sh" | bash
  else
    log_info "nvm already installed"
  fi

  export NVM_DIR="${HOME}/.nvm"
  safe_source "${NVM_DIR}/nvm.sh"

  set +e
  nvm install --lts
  nvm install node
  set -e
  nvm use node >/dev/null 2>&1 || true
}

install_uv_and_python() {
  if ! command_exists uv; then
    log_info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
  else
    log_info "uv already installed"
  fi

  safe_source "${HOME}/.local/bin/env" || true

  if command_exists uv; then
    uv python install "${PYTHON_VERSION}" || log_warn "uv python install ${PYTHON_VERSION} failed"
    uv python pin "${PYTHON_VERSION}" || true
  fi
}

install_golang() {
  if command_exists go; then
    log_info "Go already installed: $(go version)"
    return 0
  fi

  log_info "Installing Go via apt..."
  sudo apt-get install -y golang-go || log_warn "Go install failed — install manually if needed"
}

configure_docker_note() {
  if command_exists docker && docker info >/dev/null 2>&1; then
    log_info "Docker is available in WSL"
    return 0
  fi

  log_warn "Docker not available in WSL yet."
  log_warn "Enable Docker Desktop → Settings → Resources → WSL Integration for this distro,"
  log_warn "or install docker.io inside WSL if you prefer Linux-native Docker."
}

authenticate_github() {
  if run_safe gh auth status; then
    log_info "GitHub CLI already authenticated"
    return 0
  fi

  echo -n "Authenticate GitHub CLI now? (y/n): "
  read -r auth_response
  if [[ "$auth_response" =~ ^[Yy]$ ]]; then
    gh auth login
  else
    log_warn "Skipping gh auth — run 'gh auth login' later"
  fi
}

main() {
  require_wsl

  log_info "Starting WSL development environment setup..."

  install_apt_packages
  install_gh_cli
  install_oh_my_zsh
  clone_dotfiles
  ensure_dotfiles_local_gitconfig
  run_rcup "${DOTFILES_DIR}"
  run_sync_ai_assistants "${DOTFILES_DIR}"
  set_default_zsh
  install_nvm_and_node
  install_uv_and_python
  install_golang
  configure_docker_note
  authenticate_github

  log_info "WSL setup complete!"
  echo ""
  log_warn "Next steps:"
  echo "  1. Restart the shell: exec \"\$SHELL\""
  echo "  2. Open repos from the WSL path in Cursor (\\\\wsl\$\\...) so ~/.cursor symlinks resolve"
  echo "  3. Enable Docker Desktop WSL integration if you use containers"
  echo "  4. Put machine-only overrides in ~/dotfiles-local/"
}

main "$@"
