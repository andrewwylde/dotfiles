# ensure dotfiles bin directory is loaded first
PATH="$HOME/.bin:/usr/local/sbin:$PATH"

# Try loading ASDF from the regular home dir location
if [ -f "$HOME/.asdf/asdf.sh" ]; then
  . "$HOME/.asdf/asdf.sh"
elif command -v brew >/dev/null 2>&1; then
  asdf_sh="$(brew --prefix asdf 2>/dev/null)/libexec/asdf.sh"
  if [ -f "$asdf_sh" ]; then
    . "$asdf_sh"
  fi
fi

# mkdir .git/safe in the root of repositories you trust
PATH=".git/safe/../../bin:$PATH"

export -U PATH
