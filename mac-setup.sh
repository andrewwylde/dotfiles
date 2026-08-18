#!/bin/bash

################################################################################
# macOS Development Environment Setup Script
#
# This script automates the setup of a macOS development environment for me.
# engineering team members.
#
# The script is organized into logical sections:
#   1. System Prerequisites (Xcode, Rosetta, macOS preferences)
#   2. Package Management (Homebrew installation and configuration)
#   3. Development Tools (Docker, Git, Node.js, Python, Go)
#   4. Shell Configuration (zsh, oh-my-zsh, plugins)
#   5. Cloud & Infrastructure Tools (GCloud, Pulumi, cloud-sql-proxy)
#   6. Database Tools (Postgres configuration)
#
# Usage:
#   ./mac-setup.sh
#   ./setup.sh          # preferred — auto-routes by platform
#
# Requirements:
#   - macOS (tested on macOS 14.6 "Sonoma" on M3 MacBook Pro)
#   - Administrator privileges (for some operations)
################################################################################

set -e  # Exit on error

################################################################################
# Configuration and Constants
################################################################################

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# Python version to install
readonly PYTHON_VERSION="3.12"

# NVM installation version (renamed to avoid conflict with nvm.sh's internal NVM_VERSION variable)
readonly NVM_INSTALL_VERSION="v0.38.0"

################################################################################
# Utility Functions
################################################################################

# Log an informational message
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# Log a warning message
log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Log an error message
log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get the Homebrew installation path based on architecture
get_homebrew_path() {
    if [[ $(uname -m) == "arm64" ]]; then
        echo "/opt/homebrew"
    else
        echo "/usr/local"
    fi
}

# Add Homebrew to PATH for current session
setup_homebrew_path() {
    local brew_path=$(get_homebrew_path)
    export PATH="$brew_path/bin:$PATH"
}

# Add Homebrew to .zshrc if not already present
persist_homebrew_path() {
    local brew_path=$(get_homebrew_path)
    if ! grep -q "$brew_path/bin" ~/.zshrc 2>/dev/null; then
        echo "export PATH=\"$brew_path/bin:\$PATH\"" >> ~/.zshrc
    fi
}

# Source a file if it exists
safe_source() {
    if [ -f "$1" ]; then
        source "$1"
        return 0
    fi
    return 1
}

# Run a command with error handling (doesn't exit on error)
run_safe() {
    set +e
    "$@" >/dev/null 2>&1
    local exit_code=$?
    set -e
    return $exit_code
}

# Check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Get Git config value (checks both global and local config)
get_git_config() {
    local key="$1"
    # Try to get from Git config (checks ~/.gitconfig and ~/.config/git/config)
    git config --get "$key" 2>/dev/null || echo ""
}

# Show a spinner while a command runs in the background
# Usage: show_spinner "message" command [args...]
# Shows a spinner that updates in place to indicate progress
show_spinner() {
    local message="$1"
    shift
    
    # Start the command in the background, capturing output
    "$@" >/tmp/brew_output_$$.log 2>&1 &
    local pid=$!
    
    # Spinner characters
    local spinstr='|/-\'
    
    # Show spinner while process is running
    while kill -0 $pid 2>/dev/null; do
        local temp=${spinstr#?}
        printf "\r${YELLOW}[INFO]${NC} %s [%c] " "$message" "$spinstr" >&2
        local spinstr=$temp${spinstr%"$temp"}
        sleep 0.2
    done
    
    # Wait for the process to complete and get exit code
    wait $pid
    local exit_code=$?
    
    # Clear the spinner line
    printf "\r\033[K" >&2
    
    # Show the brew output
    if [ -f /tmp/brew_output_$$.log ]; then
        cat /tmp/brew_output_$$.log
        rm -f /tmp/brew_output_$$.log
    fi
    
    return $exit_code
}

################################################################################
# System Prerequisites
################################################################################

# Install Xcode Developer Tools
install_xcode_tools() {
    log_info "Installing Xcode Developer Tools..."
    if ! command_exists xcode-select || ! xcode-select -p &> /dev/null; then
        log_info "Xcode Developer Tools not found. Installing..."
        xcode-select --install
        log_warn "Please complete the Xcode Developer Tools installation in the popup window, then press Enter to continue..."
        read
    else
        log_info "Xcode Developer Tools already installed"
    fi
}

# Install Rosetta 2 for Intel compatibility
install_rosetta() {
    log_info "Installing Rosetta 2..."
    if ! /usr/bin/pgrep -q oahd; then
        log_info "Installing Rosetta 2..."
        softwareupdate --install-rosetta
    else
        log_info "Rosetta 2 already installed"
    fi
}

# Configure macOS preferences for development
configure_macos_preferences() {
    log_info "Configuring macOS preferences..."
    defaults write com.apple.finder AppleShowAllFiles YES
    defaults write com.apple.finder ShowPathbar -bool true
    defaults write com.apple.finder ShowStatusBar -bool true
    defaults write -g InitialKeyRepeat -int 10
    defaults write -g KeyRepeat -int 1
    log_info "macOS preferences configured. You may need to restart Finder (killall Finder)"
}

################################################################################
# Package Management
################################################################################

# Install Homebrew package manager
install_homebrew() {
    log_info "Installing Homebrew..."
    if ! command_exists brew; then
        log_info "Homebrew not found. Installing..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        persist_homebrew_path
    else
        log_info "Homebrew already installed"
    fi
    setup_homebrew_path
}

# Install essential command-line tools via Homebrew
install_brew_packages() {
    log_info "Installing command line essentials..."
    set +e
    brew bundle --file=- <<EOF
# macOS specific
brew "osx-cpu-temp"

# GNU Core Utilities
brew "coreutils"
brew "findutils"
brew "gnu-tar"
brew "gnu-sed"
brew "gawk"
brew "gnutls"
brew "gnu-indent"
brew "gnu-getopt"
brew "grep"
brew "bash"
brew "zsh"
brew "wget"
brew "ncdu"
brew "jq"
brew "yq"

# Compilers and build tools
brew "gcc"
brew "cmake"

# Overwrite apple provided git version with latest homebrew build
brew "git"

# File watching and monitoring
brew "entr"
brew "watch"

# Search and find tools
brew "ripgrep"
brew "fd"

# HTTP client
brew "httpie"

# GitHub helpers
brew "hub"
brew "gh"
brew "git-lfs"

# Modern replacements
brew "bat"
brew "eza"
brew "nvim"
brew "hexyl"

# Documentation
brew "tldr"
cask "basictex"

# Database dependencies
brew "sqlite"
brew "postgresql"

# Spell check
brew "ispell"

# 1Password CLI
cask "1password-cli"

# Commitizen
brew "commitizen"

EOF
    local bundle_exit=$?
    set -e
    if [ $bundle_exit -ne 0 ]; then
        log_warn "Some packages may already be installed. Continuing..."
    fi
    
    # Install gdal separately with progress indicator (can take several minutes)
    log_info "Installing gdal (this may take several minutes)..."
    if ! brew list gdal &>/dev/null; then
        set +e
        show_spinner "Installing gdal..." brew install gdal
        local gdal_exit=$?
        set -e
        if [ $gdal_exit -eq 0 ]; then
            log_info "gdal installed successfully"
        else
            log_warn "gdal installation may have failed or was already in progress"
        fi
    else
        log_info "gdal already installed"
    fi
}

################################################################################
# Docker Setup (via Colima)
################################################################################

# Install and configure Docker via Colima
# See docs/colima-setup.md for manual setup instructions
setup_docker() {
    log_info "Setting up Docker via Colima..."
    
    # Install Colima and Docker tools
    if ! command_exists colima; then
        log_info "Installing Colima..."
        brew install colima
    else
        log_info "Colima is already installed"
    fi
    
    if ! command_exists docker; then
        log_info "Installing Docker CLI..."
        brew install docker
    else
        log_info "Docker CLI is already installed"
    fi
    
    if ! command_exists docker-compose; then
        log_info "Installing Docker Compose..."
        brew install docker-compose
    else
        log_info "Docker Compose is already installed"
    fi
    
    if ! command_exists docker-buildx; then
        log_info "Installing Docker Buildx..."
        brew install docker-buildx
    else
        log_info "Docker Buildx is already installed"
    fi
    
    # Start Colima if not running
    log_info "Starting Colima..."
    if ! run_safe colima status; then
        log_info "Starting Colima..."
        colima start
    else
        log_info "Colima is already running"
    fi
    
    # Install Docker Buildx plugin
    log_info "Installing Docker Buildx plugin..."
    if run_safe docker buildx install; then
        log_info "Docker Buildx plugin installed successfully"
    else
        log_warn "Docker Buildx plugin may already be installed or installation failed"
    fi
    
    # Configure Docker config.json for compose plugin
    log_info "Configuring Docker config.json..."
    mkdir -p ~/.docker
    
    local docker_plugins_dir
    if [[ $(uname -m) == "arm64" ]]; then
        docker_plugins_dir="/opt/homebrew/lib/docker/cli-plugins"
    else
        docker_plugins_dir="/usr/local/lib/docker/cli-plugins"
    fi
    
    if [ ! -f ~/.docker/config.json ]; then
        cat > ~/.docker/config.json <<EOF
{
  "cliPluginsExtraDirs": [
    "$docker_plugins_dir"
  ]
}
EOF
        log_info "Created ~/.docker/config.json with cliPluginsExtraDirs"
    elif ! grep -q "cliPluginsExtraDirs" ~/.docker/config.json; then
        if command_exists jq; then
            jq ". + {\"cliPluginsExtraDirs\": [\"$docker_plugins_dir\"]}" ~/.docker/config.json > ~/.docker/config.json.tmp && mv ~/.docker/config.json.tmp ~/.docker/config.json
            log_info "Added cliPluginsExtraDirs to existing ~/.docker/config.json"
        else
            log_warn "jq not found. Please manually add cliPluginsExtraDirs to ~/.docker/config.json:"
            log_warn "  \"cliPluginsExtraDirs\": [\"$docker_plugins_dir\"]"
        fi
    else
        log_info "cliPluginsExtraDirs already configured in ~/.docker/config.json"
    fi
    
    # Verify Docker installation
    log_info "Verifying Docker installation..."
    if run_safe docker ps; then
        log_info "Docker is working! You can run 'docker ps' to verify."
    else
        log_warn "Docker verification failed. You may need to restart your terminal or run 'colima start'"
    fi
    
    log_info "Colima setup complete. You should be able to run 'docker compose [commands]' now."
}

################################################################################
# Shell Configuration
################################################################################

# Install and configure oh-my-zsh
install_oh_my_zsh() {
    log_info "Installing oh-my-zsh..."
    if [ ! -d "$HOME/.oh-my-zsh" ]; then
        log_warn "This will overwrite your existing ~/.zshrc file"
        log_warn "A backup will be created at ~/.zshrc.bak"
        if [ -f "$HOME/.zshrc" ]; then
            cp ~/.zshrc ~/.zshrc.bak
        fi
        
        sh -c "$(curl -fsSL https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh)" "" --unattended
        
        # Restore backup if it exists
        if [ -f "$HOME/.zshrc.bak" ]; then
            cat ~/.zshrc.bak >> ~/.zshrc
            rm ~/.zshrc.bak
        fi
    else
        log_info "oh-my-zsh already installed"
    fi
}

# Set Homebrew zsh as default shell (optional - requires sudo)
set_default_shell() {
    local zsh_bin
    if [[ $(uname -m) == "arm64" ]]; then
        zsh_bin="/opt/homebrew/bin/zsh"
    else
        zsh_bin="/usr/local/bin/zsh"
    fi
    
    if [ -f "$zsh_bin" ] && [ "$SHELL" != "$zsh_bin" ]; then
        log_info "Setting $zsh_bin as default shell..."
        sudo dscl . -create /Users/$USER UserShell "$zsh_bin"
    elif [ "$SHELL" == "$zsh_bin" ]; then
        log_info "Homebrew zsh already set as default shell"
    fi
}

# Configure Homebrew bash to ensure latest version is available
configure_bash() {
    log_info "Configuring Homebrew bash..."
    local bash_bin
    if [[ $(uname -m) == "arm64" ]]; then
        bash_bin="/opt/homebrew/bin/bash"
    else
        bash_bin="/usr/local/bin/bash"
    fi
    
    # Check if Homebrew bash is installed
    if [ ! -f "$bash_bin" ]; then
        log_warn "Homebrew bash not found at $bash_bin. It should have been installed in install_brew_packages()."
        return 1
    fi
    
    # Add Homebrew bash to /etc/shells if not already present (required for it to be used as a login shell)
    if ! grep -q "^$bash_bin$" /etc/shells 2>/dev/null; then
        log_info "Adding Homebrew bash to /etc/shells (requires sudo)..."
        echo "$bash_bin" | sudo tee -a /etc/shells > /dev/null
        log_info "Homebrew bash added to /etc/shells"
    else
        log_info "Homebrew bash already in /etc/shells"
    fi
    
    # Verify the bash version
    local bash_version=$("$bash_bin" --version | head -n1)
    log_info "Homebrew bash version: $bash_version"
    log_info "Homebrew bash is available at: $bash_bin"
    
    # Add alias to .zshrc to ensure 'bash' command uses Homebrew version
    # This ensures that when you type 'bash', it uses the Homebrew version instead of /bin/bash
    if ! grep -q "alias bash=" ~/.zshrc 2>/dev/null; then
        echo "alias bash='$bash_bin'" >> ~/.zshrc
        log_info "Added alias to .zshrc: bash -> $bash_bin"
    else
        log_info "Bash alias already configured in .zshrc"
    fi
    
    log_info "To use it, run: $bash_bin or just 'bash' (after restarting terminal)"
    log_info "To set it as your default shell, run: chsh -s $bash_bin"
}

# Install zsh syntax highlighting
install_zsh_syntax_highlighting() {
    log_info "Installing shell syntax highlighting..."
    if ! grep -q "zsh-syntax-highlighting" ~/.zshrc; then
        brew install zsh-syntax-highlighting
        echo "source $(brew --prefix)/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" >> ~/.zshrc
    else
        log_info "Shell syntax highlighting already configured"
    fi
}

# Install fzf (fuzzy finder)
install_fzf() {
    log_info "Installing fzf (fuzzy finder)..."
    if ! command_exists fzf; then
        brew install fzf
        $(brew --prefix)/opt/fzf/install --all
    else
        log_info "fzf already installed"
    fi
}

# Add helpful shell aliases
add_shell_aliases() {
    log_info "Adding helpful aliases..."
    if ! grep -q "alias erc=" ~/.zshrc; then
        cat >> ~/.zshrc <<'EOF'

# Helpful aliases
export EDITOR=nvim
alias erc="nvim ~/.zshrc && source ~/.zshrc"
alias -g vim=nvim
alias -g vi=nvim
alias dc=docker-compose
EOF
    else
        log_info "Aliases already configured"
    fi
}

################################################################################
# Git Configuration
################################################################################

# Constants for 1Password SSH key titles
get_auth_key_title() {
    echo "SSH Auth Key - $(hostname)"
}

get_signing_key_title() {
    echo "Git Signing Key - $(hostname)"
}

# Retrieve public key from 1Password with multiple fallback methods
get_1password_public_key() {
    local key_title="$1"
    if ! command_exists op; then
        echo ""
        return 1
    fi
    
    # Try multiple methods to retrieve the public key
    op item get "$key_title" --fields "public key" 2>/dev/null || \
    op item get "$key_title" --fields "public_key" 2>/dev/null || \
    op read "op://Private/$key_title/public_key" 2>/dev/null || \
    op read "op://Private/$key_title/public key" 2>/dev/null || \
    echo ""
}

# Create an SSH key in 1Password if it doesn't exist
create_1password_ssh_key() {
    local key_title="$1"
    local key_type="${2:-auth}"  # "auth" or "signing"
    
    if ! command_exists op; then
        log_error "1Password CLI (op) not found. Please install it first."
        return 1
    fi
    
    local key_description="SSH ${key_type} key"
    log_info "Creating ${key_description} in 1Password..."
    
    if ! op item get "$key_title" &>/dev/null; then
        if op item create --category=ssh --title="$key_title" --ssh-generate-key=ed25519 &>/dev/null; then
            log_info "${key_description} created in 1Password"
        else
            log_error "Failed to create ${key_description} in 1Password"
            return 1
        fi
    else
        log_info "${key_description} already exists in 1Password"
    fi
    return 0
}

# Configure Git signing with a public key
configure_git_signing_key() {
    local signing_key_public="$1"
    if [ -n "$signing_key_public" ]; then
        git config --global user.signingkey "$signing_key_public"
        git config --global commit.gpgSign true
        log_info "Git commit signing configured with 1Password SSH key"
        return 0
    else
        log_warn "Could not retrieve signing key from 1Password. You may need to configure it manually."
        return 1
    fi
}

# Add a single SSH key to GitHub
add_ssh_key_to_github_helper() {
    local key_title="$1"
    local key_type="$2"  # "auth" or "signing"
    local key_public="$3"
    
    if [ -z "$key_public" ]; then
        log_warn "Could not retrieve ${key_type} key from 1Password"
        return 1
    fi
    
    log_info "Adding SSH ${key_type} key to GitHub..."
    local key_fingerprint=$(echo "$key_public" | cut -d' ' -f2)
    
    if gh ssh-key list 2>/dev/null | grep -q "$key_fingerprint"; then
        log_info "SSH ${key_type} key is already added to GitHub"
        return 0
    fi
    
    # Create temporary file for the public key
    local temp_key_file=$(mktemp)
    echo "$key_public" > "$temp_key_file"
    
    local gh_args=()
    local title_suffix=""
    if [ "$key_type" = "signing" ]; then
        gh_args+=(--type signing)
        title_suffix="Signing Key"
    else
        title_suffix="Auth Key"
    fi
    
    if run_safe gh ssh-key add "$temp_key_file" --title "$(hostname) - ${title_suffix} - $(date +%Y-%m-%d)" "${gh_args[@]}"; then
        log_info "SSH ${key_type} key successfully added to GitHub!"
        rm -f "$temp_key_file"
        return 0
    else
        # Check again in case it was added
        if gh ssh-key list 2>/dev/null | grep -q "$key_fingerprint"; then
            log_info "SSH ${key_type} key is already added to GitHub"
            rm -f "$temp_key_file"
            return 0
        else
            log_warn "Failed to add SSH ${key_type} key to GitHub automatically."
            echo "$key_public" | pbcopy
            log_warn "SSH ${key_type} public key has been copied to your clipboard"
            if [ "$key_type" = "signing" ]; then
                log_warn "Go to https://github.com/settings/keys and add it as a signing key manually"
            else
                log_warn "Go to https://github.com/settings/keys to add it manually"
            fi
            rm -f "$temp_key_file"
            return 1
        fi
    fi
}

# Configure Git with user information and aliases
configure_git() {
    log_info "Setting up Git..."
    
    # Configure git user
    git config --global user.name "$FULL_NAME"
    git config --global user.email "$GIT_EMAIL"
    
    # Configure Git to use SSH for signing (1Password managed keys)
    log_info "Configuring Git for SSH commit signing..."
    git config --global gpg.format ssh
    
    # Get the signing key public key from 1Password
    local signing_key_title=$(get_signing_key_title)
    local signing_key_public=""
    
    # Try to get the public key from 1Password
    if command_exists op; then
        # Check if the signing key exists
        if op item get "$signing_key_title" &>/dev/null; then
            signing_key_public=$(get_1password_public_key "$signing_key_title")
            configure_git_signing_key "$signing_key_public"
        else
            log_warn "Signing key not found in 1Password. It will be created in the next step."
        fi
    else
        log_warn "1Password CLI not found. Git signing will need to be configured manually."
    fi
    
    # Add git aliases
    if ! grep -q "\[alias\]" ~/.gitconfig; then
        cat >> ~/.gitconfig <<'EOF'
[alias]
	lg = log --graph --all --decorate --oneline
	st = status
	co = checkout
EOF
    else
        log_info "Git aliases already configured"
    fi
}

# Generate SSH keys using 1Password CLI for both authentication and signing
generate_ssh_key() {
    log_info "Setting up SSH keys using 1Password CLI..."
    
    if ! command_exists op; then
        log_error "1Password CLI (op) not found. Please install it first."
        return 1
    fi
    
    # Check if user is signed in to 1Password
    if ! run_safe op account list &>/dev/null; then
        log_warn "Not signed in to 1Password CLI. Attempting to sign in..."
        log_warn "You'll need to authenticate with 1Password. This may open a browser window."
        if ! op signin; then
            log_error "Failed to sign in to 1Password CLI. Please sign in manually: op signin"
            return 1
        fi
    fi
    
    # Create SSH keys
    local auth_key_title=$(get_auth_key_title)
    local signing_key_title=$(get_signing_key_title)
    
    create_1password_ssh_key "$auth_key_title" "authentication" || return 1
    create_1password_ssh_key "$signing_key_title" "signing" || return 1
    
    # Configure SSH to use 1Password SSH Agent
    log_info "Configuring SSH to use 1Password SSH Agent..."
    if [ ! -f ~/.ssh/config ]; then
        touch ~/.ssh/config
        chmod 600 ~/.ssh/config
    fi
    
    # Check if 1Password SSH Agent is already configured
    if ! grep -q "IdentityAgent.*1password" ~/.ssh/config; then
        # Add 1Password SSH Agent configuration
        if ! grep -q "^Host \*" ~/.ssh/config; then
            cat >> ~/.ssh/config <<'EOF'

Host *
  IdentityAgent ~/.1password/agent.sock
EOF
        else
            # Add IdentityAgent to existing Host * block if not present
            if ! grep -A 10 "^Host \*" ~/.ssh/config | grep -q "IdentityAgent"; then
                # Use a temporary file to add the line after "Host *"
                local temp_config=$(mktemp)
                awk '/^Host \*/ {print; print "  IdentityAgent ~/.1password/agent.sock"; next} {print}' ~/.ssh/config > "$temp_config"
                mv "$temp_config" ~/.ssh/config
                chmod 600 ~/.ssh/config
            fi
        fi
        log_info "SSH configured to use 1Password SSH Agent"
    else
        log_info "SSH already configured to use 1Password SSH Agent"
    fi
    
    # Update Git signing key configuration now that the key exists
    local signing_key_public=$(get_1password_public_key "$signing_key_title")
    configure_git_signing_key "$signing_key_public"
}

# Automatically add SSH keys to GitHub using GitHub CLI
add_ssh_key_to_github() {
    log_info "Attempting to add SSH keys to GitHub..."
    
    if ! command_exists op; then
        log_warn "1Password CLI (op) not found. Cannot retrieve SSH keys."
        return
    fi
    
    if ! command_exists gh; then
        log_warn "GitHub CLI (gh) not found. Cannot automatically add SSH key to GitHub."
        log_warn "Please add your SSH keys manually from 1Password:"
        log_warn "1. Go to https://github.com/settings/keys"
        log_warn "2. Click 'New SSH key'"
        log_warn "3. Copy the public key from 1Password and paste it"
        return
    fi
    
    # Check if user is already authenticated
    local auth_response="yes"
    if ! run_safe gh auth status; then
        log_info "GitHub CLI authentication required to add SSH key automatically"
        log_warn "You'll need to authenticate with GitHub. This will open a browser window."
        echo -n "Do you want to authenticate with GitHub now? (y/n): "
        read -r auth_response
        if [[ "$auth_response" =~ ^[Yy]$ ]]; then
            log_info "Authenticating with GitHub..."
            log_info "Requesting permissions for SSH key management (admin:public_key, admin:ssh_signing_key)..."
            gh auth login --web --git-protocol ssh --hostname github.com --scopes "admin:public_key,admin:ssh_signing_key"
        else
            log_warn "Skipping GitHub authentication. You can add the SSH key manually later."
            auth_response="skip"
        fi
    else
        log_info "Already authenticated with GitHub CLI"
        # Check if we have the required scopes (admin:public_key, admin:ssh_signing_key)
        # If not, we'll try to add keys anyway and let GitHub CLI handle the error
        log_info "Note: If key addition fails, you may need to re-authenticate with:"
        log_info "  gh auth login --web --git-protocol ssh --hostname github.com --scopes 'admin:public_key,admin:ssh_signing_key'"
    fi
    
    # Add SSH keys to GitHub if authenticated
    if [ "$auth_response" != "skip" ] && run_safe gh auth status; then
        # Get keys from 1Password and add to GitHub
        local auth_key_title=$(get_auth_key_title)
        local signing_key_title=$(get_signing_key_title)
        
        local auth_key_public=$(get_1password_public_key "$auth_key_title")
        add_ssh_key_to_github_helper "$auth_key_title" "authentication" "$auth_key_public"
        
        local signing_key_public=$(get_1password_public_key "$signing_key_title")
        add_ssh_key_to_github_helper "$signing_key_title" "signing" "$signing_key_public"
    fi
}

################################################################################
# Node.js Setup (via nvm)
################################################################################

# Install and configure Node.js via nvm
setup_nodejs() {
    log_info "Setting up Node.js via nvm..."
    
    if [ ! -d "$HOME/.nvm" ]; then
        curl -o- "https://raw.githubusercontent.com/nvm-sh/nvm/${NVM_INSTALL_VERSION}/install.sh" | zsh
        
        # Source nvm in current shell
        export NVM_DIR="$HOME/.nvm"
        safe_source "$NVM_DIR/nvm.sh"
        
        # Add to .zshrc if not already there
        if ! grep -q "NVM_DIR" ~/.zshrc; then
            cat >> ~/.zshrc <<'EOF'

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && . "$NVM_DIR/bash_completion"
EOF
        fi
    else
        log_info "nvm already installed"
        export NVM_DIR="$HOME/.nvm"
        safe_source "$NVM_DIR/nvm.sh"
    fi
    
    # Install Node.js versions
    log_info "Installing Node.js versions..."
    set +e
    nvm install node
    nvm install --lts
    set -e
    
    nvm use node
}

################################################################################
# Python Setup
################################################################################

# Install uv for Python version management
install_uv() {
    log_info "Installing uv for Python version management..."
    if ! command_exists uv; then
        set +e
        curl -LsSf https://astral.sh/uv/install.sh | sh
        local uv_install_exit=$?
        set -e
        
        # Check if uv was installed successfully
        if [ -f "$HOME/.local/bin/uv" ]; then
            log_info "uv installed successfully"
            safe_source "$HOME/.local/bin/env"
            log_info "Sourced uv environment configuration"
        elif command_exists uv; then
            log_info "uv is available in PATH"
        elif [ $uv_install_exit -ne 0 ]; then
            log_warn "uv installation may have failed. Exit code: $uv_install_exit"
            log_warn "You can install uv manually: curl -LsSf https://astral.sh/uv/install.sh | sh"
        fi
        
        # Add uv env sourcing to .zshrc if not already there
        if [ -f "$HOME/.local/bin/env" ] && ! grep -q "\.local/bin/env" ~/.zshrc; then
            echo 'source "$HOME/.local/bin/env"' >> ~/.zshrc
            log_info "Added uv environment sourcing to ~/.zshrc"
        fi
    else
        log_info "uv is already installed"
    fi
    
    # Ensure uv is available in PATH for the rest of the script
    # Only source if the file exists (uv may be installed via other methods)
    if [ -f "$HOME/.local/bin/env" ]; then
        safe_source "$HOME/.local/bin/env"
    elif command_exists uv; then
        log_info "uv is available in PATH"
    fi
}

# Install and configure Python 3.12 as the default Python version via uv
setup_python_314() {
    log_info "Installing Python ${PYTHON_VERSION} and configuring it as the default..."
    if ! command_exists uv; then
        log_warn "uv not available. Cannot install Python ${PYTHON_VERSION} via uv."
        return
    fi
    
    # Always install Python 3.12 via uv to ensure it's in uv's managed location
    log_info "Installing Python ${PYTHON_VERSION} via uv (will use uv's managed location)..."
    set +e
    uv python install "${PYTHON_VERSION}"
    local uv_python_install_exit=$?
    set -e
    
    if [ $uv_python_install_exit -eq 0 ]; then
        log_info "Python ${PYTHON_VERSION} installed/verified via uv"
    else
        log_warn "Failed to install Python ${PYTHON_VERSION} via uv. Exit code: $uv_python_install_exit"
        log_warn "You can install Python ${PYTHON_VERSION} manually: uv python install ${PYTHON_VERSION}"
    fi
    
    # Pin Python 3.12 as the default
    log_info "Configuring Python ${PYTHON_VERSION} as the default version..."
    set +e
    uv python pin "${PYTHON_VERSION}"
    local uv_pin_exit=$?
    set -e
    
    if [ $uv_pin_exit -eq 0 ]; then
        log_info "Python ${PYTHON_VERSION} pinned as the default version via uv"
    else
        log_warn "Failed to pin Python ${PYTHON_VERSION} as default, but it should still be available"
    fi
    
    # Verify Python 3.12 is available and configured
    set +e
    local uv_python_314=$(uv python find "${PYTHON_VERSION}" 2>/dev/null)
    set -e
    if [ -n "$uv_python_314" ]; then
        log_info "Python ${PYTHON_VERSION} is available and configured as the default via uv"
        log_info "Python ${PYTHON_VERSION} location: $uv_python_314"
    else
        log_warn "Python ${PYTHON_VERSION} may not be fully configured. You may need to run 'uv python pin ${PYTHON_VERSION}' manually"
    fi
}

################################################################################
# Go Setup
################################################################################

# Install and configure Go (golang)
setup_golang() {
    log_info "Setting up Go (golang)..."
    
    if ! command_exists go; then
        log_info "Installing Go via Homebrew..."
        brew install go
    else
        log_info "Go is already installed"
    fi
    
    # Verify Go installation
    if command_exists go; then
        local go_version=$(go version)
        log_info "Go installed successfully: $go_version"
        
        # Configure GOPATH and GOROOT if not already set
        if ! grep -q "GOPATH" ~/.zshrc 2>/dev/null; then
            cat >> ~/.zshrc <<'EOF'

# Go configuration
export GOPATH="$HOME/go"
export PATH="$GOPATH/bin:$PATH"
EOF
            log_info "Added Go environment variables to ~/.zshrc"
        else
            log_info "Go environment variables already configured in ~/.zshrc"
        fi
        
        # Export for current session
        export GOPATH="$HOME/go"
        export PATH="$GOPATH/bin:$PATH"
    else
        log_warn "Go installation may have failed. You can install it manually: brew install go"
    fi
}

################################################################################
# Cloud & Infrastructure Tools
################################################################################

# Install Pulumi for infrastructure as code
install_pulumi() {
    log_info "Installing Pulumi..."
    if ! command_exists pulumi; then
        brew install pulumi
    else
        log_info "Pulumi is already installed"
    fi
}

# Install Google Cloud CLI
install_gcloud() {
    log_info "Installing Google Cloud CLI..."
    if ! command_exists gcloud; then
        brew install --cask google-cloud-sdk
        log_info "Google Cloud SDK installed. You'll need to run 'gcloud auth login' to authenticate."
    else
        log_info "Google Cloud CLI is already installed"
    fi
}

# Install cloud-sql-proxy for secure database connections
install_cloud_sql_proxy() {
    log_info "Installing cloud-sql-proxy..."
    if ! command_exists cloud-sql-proxy; then
        brew install cloud-sql-proxy
    else
        log_info "cloud-sql-proxy is already installed"
    fi
}

################################################################################
# Database Tools
################################################################################

# Configure Postgres client settings
configure_postgres() {
    log_info "Setting up Postgres configuration..."
    
    # Create .psqlrc file
    if [ ! -f ~/.psqlrc ]; then
        cat > ~/.psqlrc <<'EOF'
-- By default, NULL displays as an empty space. Is it actually an empty
-- string, or is it null? This makes that distinction visible.
\pset null '[NULL]'

-- Use table format (with headers across the top) by default, but switch to
-- expanded table format when there's a lot of data, which makes it much
-- easier to read.
\x auto

-- Verbose error reports.
\set VERBOSITY verbose

-- Use a separate history file per-database.
\set HISTFILE ~/.psql_history- :DBNAME

-- If a command is run more than once in a row, only store it once in the
-- history.
\set HISTCONTROL ignoredups

-- Autocomplete keywords (like SELECT) in upper-case, even if you started
-- typing them in lower case.
\set COMP_KEYWORD_CASE upper

-- Wrap long output
\pset format wrapped
EOF
        log_info ".psqlrc file created"
    else
        log_info ".psqlrc file already exists"
    fi
    
    # Install Postico (Postgres GUI)
    log_info "Installing Postico (Postgres GUI)..."
    if ! brew list --cask postico &> /dev/null; then
        brew install --cask postico
    else
        log_info "Postico already installed"
    fi
}

################################################################################
# Main Execution
################################################################################

main() {
    # Check if running on macOS
    if [[ "$OSTYPE" != "darwin"* ]]; then
        log_error "This script is designed for macOS only"
        exit 1
    fi
    
    log_info "Starting Dev setup for macOS..."
    
    # Check for required user input (check Git config first, then environment variables, then prompt)
    if [ -z "$GIT_EMAIL" ]; then
        GIT_EMAIL=$(get_git_config "user.email")
        if [ -z "$GIT_EMAIL" ]; then
            echo -n "Enter your GitHub email"
            read GIT_EMAIL
        else
            log_info "Using Git email from config: $GIT_EMAIL"
        fi
        export GIT_EMAIL
    fi
    
    if [ -z "$FULL_NAME" ]; then
        FULL_NAME=$(get_git_config "user.name")
        if [ -z "$FULL_NAME" ]; then
            echo -n "Enter your full name (e.g., First Last): "
            read FULL_NAME
        else
            log_info "Using Git name from config: $FULL_NAME"
        fi
        export FULL_NAME
    fi
    
    # System Prerequisites
    install_xcode_tools
    install_rosetta
    configure_macos_preferences
    
    # Package Management
    install_homebrew
    install_brew_packages
    
    # Development Tools
    setup_docker
    configure_git
    generate_ssh_key
    add_ssh_key_to_github
    setup_nodejs
    
    # Python Setup
    install_uv
    setup_python_314
    
    # Go Setup
    setup_golang
    
    # Shell Configuration
    install_oh_my_zsh
    set_default_shell
    configure_bash
    install_zsh_syntax_highlighting
    install_fzf
    add_shell_aliases
    
    # Cloud & Infrastructure Tools
    install_pulumi
    install_gcloud
    install_cloud_sql_proxy
    
    # Database Tools
    configure_postgres

    # Dotfiles harness: agent-sync + rcup (parity with wsl-setup)
    local repo_root
    repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [[ -f "${repo_root}/setup/common.sh" ]]; then
      # shellcheck source=setup/common.sh
      source "${repo_root}/setup/common.sh"
      install_agent_sync "${repo_root}"
      if command_exists rcup; then
        run_rcup "${repo_root}" || log_warn "rcup failed or rcm missing"
      else
        log_warn "rcm/rcup not installed; skip rcup (brew install rcm)"
      fi
      run_agent_sync "${repo_root}" 1
    fi
    
    # Final instructions
    log_info "Setup complete!"
    echo ""
    log_warn "IMPORTANT: Please complete the following steps manually:"
    echo "  1. Restart your terminal or run: exec \"\$SHELL\""
    echo "  2. Authenticate with Google Cloud: gcloud auth login && gcloud auth application-default login"
    echo ""
    log_info "You may also want to restart Finder to see hidden files: killall Finder"
}

# Run main function
main "$@"
