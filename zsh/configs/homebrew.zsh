# Homebrew (macOS only — skipped on WSL/Linux)
if [[ "$(uname -s)" != "Darwin" ]]; then
  return 0
fi

# To opt in to Homebrew analytics, `unset` this in ~/.zshrc.local .
# Learn more about what you are opting in to at
# https://docs.brew.sh/Analytics
export HOMEBREW_NO_ANALYTICS=1

# postgresql@16 is keg-only; add psql to PATH
if [[ -d /opt/homebrew/opt/postgresql@16/bin ]]; then
  export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
fi
