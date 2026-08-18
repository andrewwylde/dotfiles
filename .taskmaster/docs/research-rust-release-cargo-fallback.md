# Research: Rust Release Binaries + Cargo Fallback
<!-- Task Master: agent-sync / Task #4 -->

**Status:** Draft — 2026-08-17  
**Scope:** Asset naming · CI matrix · setup.sh / setup.ps1 detection logic  
**Platforms:** darwin-arm64, linux-amd64, linux-arm64 (incl. Raspberry Pi), windows-amd64 (incl. WSL)

---

## 1. Summary

The most reliable cross-platform Rust CLI install strategy is:

1. **Detect** OS + architecture in the installer script.
2. **Download** the matching prebuilt tarball/zip from the GitHub Release.
3. **Verify** the SHA-256 sidecar.
4. **Install** the binary to `~/.cargo/bin` (or `~/.local/bin`).
5. **Fallback:** if no prebuilt exists for this triple, try `cargo install <crate> --locked`.
6. **Bootstrap:** if cargo is absent, print a `rustup` install link and exit 1.

This design ships fast paths for the four primary triples and degrades gracefully
to any Rust-supported target via source build.

---

## 2. Canonical Asset Names

### 2.1 Naming Convention

The community has converged on two styles:

| Style | Example |
|---|---|
| **Friendly** (`os-arch`) | `agent-sync-darwin-arm64.tar.gz` |
| **Rust-target** | `agent-sync-aarch64-apple-darwin.tar.gz` |

**Recommendation for agent-sync:** use the **friendly** style — it maps
directly to the `uname`-based detection logic in scripts, avoids Rust-triple
knowledge leaking into install scripts, and matches how real projects ship
(fyi-cli, klaas, truffle, figctl, etc.).

### 2.2 Concrete Asset List

Every release MUST contain these files:

```
agent-sync-darwin-arm64.tar.gz
agent-sync-darwin-arm64.tar.gz.sha256
agent-sync-linux-amd64.tar.gz
agent-sync-linux-amd64.tar.gz.sha256
agent-sync-linux-arm64.tar.gz
agent-sync-linux-arm64.tar.gz.sha256
agent-sync-windows-amd64.zip
agent-sync-windows-amd64.zip.sha256
```

Optional (strongly recommended for Alpine / musl-only containers):

```
agent-sync-linux-amd64-musl.tar.gz
agent-sync-linux-amd64-musl.tar.gz.sha256
agent-sync-linux-arm64-musl.tar.gz
agent-sync-linux-arm64-musl.tar.gz.sha256
```

Archive internals: each tarball/zip contains **only the binary** at the root
(`agent-sync` or `agent-sync.exe`). No subdirectory. This simplifies
extraction to a single `tar -xz -C <dest>`.

SHA-256 sidecar format (one line, standard `sha256sum` output):

```
<hex>  agent-sync-darwin-arm64.tar.gz
```

---

## 3. GitHub Actions CI Matrix

### 3.1 Rust target → friendly asset mapping

| Friendly name | Rust target | Runner | Linker notes |
|---|---|---|---|
| `darwin-arm64` | `aarch64-apple-darwin` | `macos-latest` | native, no cross |
| `linux-amd64` | `x86_64-unknown-linux-gnu` | `ubuntu-latest` | native |
| `linux-amd64-musl` | `x86_64-unknown-linux-musl` | `ubuntu-latest` | `musl-tools` apt pkg |
| `linux-arm64` | `aarch64-unknown-linux-gnu` | `ubuntu-24.04-arm` | native arm64 runner (free since 2025) |
| `linux-arm64-musl` | `aarch64-unknown-linux-musl` | `ubuntu-24.04-arm` | `musl-tools` or `cross` |
| `windows-amd64` | `x86_64-pc-windows-msvc` | `windows-latest` | native |

> **Note:** GitHub's free `ubuntu-24.04-arm` runners (native aarch64) became
> available in 2025. cargo-dist v0.30.0 (Sep 2025) switched to these by
> default, eliminating cross-compilation complexity for linux-arm64.

### 3.2 Annotated release.yml

```yaml
name: Release

on:
  push:
    tags: ["v[0-9]+.[0-9]+.[0-9]+*"]

permissions:
  contents: write

env:
  BINARY: agent-sync
  CRATE:  agent-sync   # crates.io crate name

jobs:
  build:
    name: Build ${{ matrix.asset_name }}
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        include:
          # ── macOS Apple Silicon ─────────────────────────────────────────
          - os: macos-latest
            target: aarch64-apple-darwin
            asset_name: agent-sync-darwin-arm64
            archive_ext: .tar.gz

          # ── Linux x86_64 (glibc) ────────────────────────────────────────
          - os: ubuntu-latest
            target: x86_64-unknown-linux-gnu
            asset_name: agent-sync-linux-amd64
            archive_ext: .tar.gz

          # ── Linux x86_64 (musl / Alpine) ────────────────────────────────
          - os: ubuntu-latest
            target: x86_64-unknown-linux-musl
            asset_name: agent-sync-linux-amd64-musl
            archive_ext: .tar.gz
            musl: true

          # ── Linux ARM64 (glibc, native runner) ──────────────────────────
          - os: ubuntu-24.04-arm          # free native arm64 runner
            target: aarch64-unknown-linux-gnu
            asset_name: agent-sync-linux-arm64
            archive_ext: .tar.gz

          # ── Linux ARM64 (musl) ───────────────────────────────────────────
          - os: ubuntu-24.04-arm
            target: aarch64-unknown-linux-musl
            asset_name: agent-sync-linux-arm64-musl
            archive_ext: .tar.gz
            musl: true

          # ── Windows x86_64 (MSVC) ────────────────────────────────────────
          - os: windows-latest
            target: x86_64-pc-windows-msvc
            asset_name: agent-sync-windows-amd64
            archive_ext: .zip

    steps:
      - uses: actions/checkout@v4

      - name: Install Rust toolchain
        uses: dtolnay/rust-toolchain@stable
        with:
          targets: ${{ matrix.target }}

      - name: Install musl-tools (if needed)
        if: matrix.musl == true
        run: |
          sudo apt-get update -qq
          sudo apt-get install -y musl-tools

      - name: Cache cargo
        uses: Swatinem/rust-cache@v2
        with:
          key: ${{ matrix.target }}

      - name: Build release binary
        run: cargo build --release --locked --target ${{ matrix.target }}

      # Strip debug symbols (Linux / macOS only)
      - name: Strip binary
        if: runner.os != 'Windows'
        run: strip target/${{ matrix.target }}/release/${{ env.BINARY }} || true

      # ── Package ─────────────────────────────────────────────────────────
      - name: Package (Unix)
        if: runner.os != 'Windows'
        shell: bash
        run: |
          BIN=target/${{ matrix.target }}/release/${{ env.BINARY }}
          ARCHIVE="${{ matrix.asset_name }}${{ matrix.archive_ext }}"
          tar -czf "$ARCHIVE" -C "$(dirname "$BIN")" "$(basename "$BIN")"
          sha256sum "$ARCHIVE" > "$ARCHIVE.sha256"
          echo "ARCHIVE=$ARCHIVE" >> "$GITHUB_ENV"

      - name: Package (Windows)
        if: runner.os == 'Windows'
        shell: pwsh
        run: |
          $bin = "target\${{ matrix.target }}\release\${{ env.BINARY }}.exe"
          $archive = "${{ matrix.asset_name }}${{ matrix.archive_ext }}"
          Compress-Archive -Path $bin -DestinationPath $archive
          $hash = (Get-FileHash $archive -Algorithm SHA256).Hash.ToLower()
          "$hash  $archive" | Out-File -Encoding ascii "${archive}.sha256"
          "ARCHIVE=$archive" | Out-File -Append $env:GITHUB_ENV

      # ── Upload to Release ────────────────────────────────────────────────
      - name: Upload release asset
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh release upload "${{ github.ref_name }}" \
            "${{ env.ARCHIVE }}" \
            "${{ env.ARCHIVE }}.sha256" \
            --clobber
```

---

## 4. OS / Arch Detection Logic

### 4.1 Decision tree

```
uname -s
├── Darwin  → OS=darwin
│   uname -m
│   ├── arm64       → ARCH=arm64      → darwin-arm64
│   └── x86_64      → no prebuilt (cargo fallback)
│
├── Linux
│   /proc/version contains "Microsoft" or "WSL"?
│   ├── yes → IS_WSL=1 (still treated as Linux; download Linux binary)
│   └── no  → IS_WSL=0
│
│   uname -m
│   ├── x86_64  → ARCH=amd64    → linux-amd64  (glibc or musl)
│   ├── aarch64 → ARCH=arm64    → linux-arm64  (Pi 4/5 64-bit OS, AWS Graviton)
│   └── armv7l  → no prebuilt   → cargo fallback (Pi 32-bit OS / older Pi)
│
└── MINGW* / MSYS* / CYGWIN* → treat as Windows (use setup.ps1)
```

**Raspberry Pi specifics:**
- Pi 4/5 running 64-bit Raspberry Pi OS → `uname -m` = `aarch64` → maps to
  `linux-arm64` binary. ✅ prebuilt works.
- Pi 4/5 running 32-bit Raspberry Pi OS → `uname -m` = `armv7l` → no
  prebuilt; fall back to `cargo install`. The kernel reports `aarch64` but
  `uname -m` on a 32-bit userland returns `armv7l`, which is the correct
  detection signal.
- Pi 3 (and earlier) → typically `armv7l` or `armv6l` → cargo fallback only.

**WSL specifics:**
- WSL1 and WSL2 both report `Linux` in `uname -s`; `/proc/version` contains
  `Microsoft` (case-insensitive). Always download the `linux-amd64` or
  `linux-arm64` binary — do **not** download the Windows binary inside WSL.
- WSL users who invoke `setup.ps1` from a Windows terminal will get the
  Windows binary path automatically.

**musl selection heuristic (Linux):**
```bash
is_musl() {
  ldd --version 2>&1 | grep -qi musl && return 0
  # Alpine: /bin/sh is busybox
  [ -f /etc/alpine-release ] && return 0
  return 1
}
```
Fall back to `linux-<arch>-musl` variant when `is_musl` is true; otherwise
use the glibc variant (which covers Raspberry Pi OS, Ubuntu, Debian, etc.).

---

## 5. setup.sh — Install Script Pseudocode

```bash
#!/usr/bin/env bash
# setup.sh  –  install agent-sync (prefer prebuilt, fall back to cargo)
# Usage: curl -fsSL https://raw.githubusercontent.com/OWNER/agent-sync/main/setup.sh | bash
#        AGENT_SYNC_VERSION=v1.2.3 bash setup.sh   # pin a version

set -euo pipefail

REPO="OWNER/agent-sync"
BINARY="agent-sync"
CRATE="agent-sync"
INSTALL_DIR="${AGENT_SYNC_INSTALL_DIR:-$HOME/.cargo/bin}"
VERSION="${AGENT_SYNC_VERSION:-latest}"

# ── Helpers ──────────────────────────────────────────────────────────────
info()  { printf '\033[1;34m  =>\033[0m %s\n' "$*"; }
ok()    { printf '\033[1;32m  ✓\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33m  !\033[0m %s\n' "$*"; }
die()   { printf '\033[1;31m  ✗\033[0m %s\n' "$*" >&2; exit 1; }

need_cmd() { command -v "$1" >/dev/null 2>&1 || die "required: $1"; }

# ── Detect OS ────────────────────────────────────────────────────────────
detect_os() {
  local uname_s
  uname_s="$(uname -s 2>/dev/null)"
  case "$uname_s" in
    Darwin)                OS="darwin" ;;
    Linux)
      # WSL: /proc/version contains "Microsoft" (case-insensitive)
      if [[ -r /proc/version ]] && grep -qi "microsoft\|wsl" /proc/version 2>/dev/null; then
        IS_WSL=1
      fi
      OS="linux"
      ;;
    MINGW*|MSYS*|CYGWIN*)  die "Windows detected — run setup.ps1 instead" ;;
    *)                     die "Unsupported OS: $uname_s" ;;
  esac
}

# ── Detect Architecture ───────────────────────────────────────────────────
detect_arch() {
  local uname_m
  uname_m="$(uname -m 2>/dev/null)"
  case "$uname_m" in
    x86_64|amd64)    ARCH="amd64" ;;
    aarch64|arm64)   ARCH="arm64" ;;
    armv7l|armv6l)
      # 32-bit ARM (e.g. Pi running 32-bit OS) — no prebuilt binary
      warn "32-bit ARM detected ($uname_m): no prebuilt binary; will try cargo install."
      ARCH="unsupported"
      ;;
    *)               die "Unsupported architecture: $uname_m" ;;
  esac
}

# ── Detect musl vs glibc (Linux only) ────────────────────────────────────
detect_libc() {
  LIBC="gnu"
  if [[ "$OS" == "linux" ]]; then
    if ldd --version 2>&1 | grep -qi musl || [[ -f /etc/alpine-release ]]; then
      LIBC="musl"
    fi
  fi
}

# ── Resolve GitHub release URL ────────────────────────────────────────────
resolve_url() {
  # Determine friendly asset name
  local suffix=""
  [[ "$OS" == "linux" && "$LIBC" == "musl" ]] && suffix="-musl"

  ASSET_NAME="${BINARY}-${OS}-${ARCH}${suffix}"

  if [[ "$OS" == "windows" ]]; then
    ASSET_FILE="${ASSET_NAME}.zip"
  else
    ASSET_FILE="${ASSET_NAME}.tar.gz"
  fi

  if [[ "$VERSION" == "latest" ]]; then
    BASE_URL="https://github.com/${REPO}/releases/latest/download"
  else
    BASE_URL="https://github.com/${REPO}/releases/download/${VERSION}"
  fi

  ASSET_URL="${BASE_URL}/${ASSET_FILE}"
  CHECKSUM_URL="${ASSET_URL}.sha256"
}

# ── Download and verify ───────────────────────────────────────────────────
download_and_verify() {
  local tmp
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT

  info "Downloading $ASSET_URL"
  if ! curl --proto '=https' --tlsv1.2 -fsSL --retry 3 -o "$tmp/$ASSET_FILE" "$ASSET_URL"; then
    warn "Download failed (HTTP 404 or network error)."
    return 1
  fi

  info "Verifying checksum"
  curl --proto '=https' --tlsv1.2 -fsSL --retry 3 -o "$tmp/${ASSET_FILE}.sha256" "$CHECKSUM_URL" || {
    warn "Checksum file not found; skipping verification."
  }
  if [[ -f "$tmp/${ASSET_FILE}.sha256" ]]; then
    (cd "$tmp" && sha256sum -c "${ASSET_FILE}.sha256" --status) \
      || die "Checksum mismatch — aborting."
  fi

  info "Installing to $INSTALL_DIR"
  mkdir -p "$INSTALL_DIR"
  tar -xzf "$tmp/$ASSET_FILE" -C "$INSTALL_DIR" "$BINARY"
  chmod +x "$INSTALL_DIR/$BINARY"

  INSTALLED=1
}

# ── cargo install fallback ────────────────────────────────────────────────
cargo_install_fallback() {
  if command -v cargo >/dev/null 2>&1; then
    info "Falling back to: cargo install $CRATE --locked"
    if [[ "$VERSION" == "latest" ]]; then
      cargo install "$CRATE" --locked
    else
      cargo install "$CRATE" --locked --version "${VERSION#v}"
    fi
    ok "Installed via cargo (binary in ~/.cargo/bin)"
    INSTALLED=1
  else
    warn "cargo not found on PATH."
    info "Install Rust first:  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    return 1
  fi
}

# ── PATH note ────────────────────────────────────────────────────────────
ensure_path() {
  if ! echo "$PATH" | tr ':' '\n' | grep -qx "$INSTALL_DIR"; then
    warn "$INSTALL_DIR is not in PATH."
    info "Add to your shell profile:"
    echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
  fi
}

# ── Main ─────────────────────────────────────────────────────────────────
main() {
  need_cmd curl
  need_cmd tar

  detect_os
  detect_arch
  detect_libc

  INSTALLED=0

  if [[ "$ARCH" != "unsupported" ]]; then
    resolve_url
    download_and_verify || true   # allow fallthrough on failure
  fi

  if [[ "$INSTALLED" -eq 0 ]]; then
    cargo_install_fallback || die "Installation failed. See messages above."
  fi

  ok "agent-sync installed: $("$INSTALL_DIR/$BINARY" --version 2>/dev/null || echo '(check PATH)')"
  ensure_path

  [[ "${IS_WSL:-0}" -eq 1 ]] && info "WSL detected. Binary is the Linux build (correct)."
}

main "$@"
```

---

## 6. setup.ps1 — Windows Install Script Pseudocode

```powershell
#Requires -Version 5.1
<#
.SYNOPSIS
  Install agent-sync on Windows (prefer prebuilt, fall back to cargo).
.PARAMETER Version
  Release tag to install (default: latest).
.PARAMETER InstallDir
  Target directory (default: $env:CARGO_HOME\bin or $HOME\.cargo\bin).
#>
[CmdletBinding()]
param(
  [string]$Version    = $env:AGENT_SYNC_VERSION ?? "latest",
  [string]$InstallDir = ""
)

$ErrorActionPreference = "Stop"

$Repo   = "OWNER/agent-sync"
$Binary = "agent-sync"
$Crate  = "agent-sync"

# ── Resolve install dir ───────────────────────────────────────────────────
if (-not $InstallDir) {
  $cargoHome = if ($env:CARGO_HOME) { $env:CARGO_HOME }
               else { Join-Path $HOME ".cargo" }
  $InstallDir = Join-Path $cargoHome "bin"
}
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# ── Detect architecture ───────────────────────────────────────────────────
function Get-Arch {
  # Use RuntimeInformation for correctness on ARM Windows
  try {
    Add-Type -AssemblyName "System.Runtime.InteropServices.RuntimeInformation" -ErrorAction Stop
    $arch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
  } catch {
    $arch = $env:PROCESSOR_ARCHITECTURE
  }
  switch ($arch) {
    "X64"   { return "amd64" }
    "AMD64" { return "amd64" }
    "Arm64" { return "arm64" }
    default { return $null }
  }
}

# ── Resolve asset URL ─────────────────────────────────────────────────────
function Get-AssetUrl {
  param([string]$Arch, [string]$Ver)
  $assetName = "agent-sync-windows-$Arch"
  $assetFile = "$assetName.zip"
  $base = if ($Ver -eq "latest") {
    "https://github.com/$Repo/releases/latest/download"
  } else {
    "https://github.com/$Repo/releases/download/$Ver"
  }
  return @{
    Asset    = "$base/$assetFile"
    Checksum = "$base/$assetFile.sha256"
    FileName = $assetFile
  }
}

# ── Download and verify ───────────────────────────────────────────────────
function Install-Prebuilt {
  param([hashtable]$Urls)

  $tmp = [System.IO.Path]::GetTempPath()
  $archive = Join-Path $tmp $Urls.FileName
  $shaFile = "$archive.sha256"

  Write-Host "  => Downloading $($Urls.Asset)"
  try {
    Invoke-WebRequest -Uri $Urls.Asset    -OutFile $archive -UseBasicParsing
    Invoke-WebRequest -Uri $Urls.Checksum -OutFile $shaFile  -UseBasicParsing
  } catch {
    Write-Warning "  ! Download failed: $_"
    return $false
  }

  # Verify SHA-256
  $expected = (Get-Content $shaFile -Raw).Trim().Split(' ')[0]
  $actual   = (Get-FileHash $archive -Algorithm SHA256).Hash.ToLower()
  if ($expected -ne $actual) {
    Write-Error "  ✗ Checksum mismatch — aborting."
    return $false
  }
  Write-Host "  => Checksum OK"

  # Extract binary
  $extractDir = Join-Path $tmp "agent-sync-extract"
  Expand-Archive -Path $archive -DestinationPath $extractDir -Force
  $exePath = Join-Path $extractDir "$Binary.exe"
  Copy-Item -Path $exePath -Destination (Join-Path $InstallDir "$Binary.exe") -Force

  # Cleanup
  Remove-Item -Recurse -Force $extractDir, $archive, $shaFile -ErrorAction SilentlyContinue

  return $true
}

# ── cargo install fallback ────────────────────────────────────────────────
function Install-ViaCargo {
  if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Warning "  ! cargo not found."
    Write-Host "    Install Rust: https://rustup.rs"
    return $false
  }
  Write-Host "  => Falling back to: cargo install $Crate --locked"
  if ($Version -eq "latest") {
    $args = @($Crate, "--locked")
  } else {
    $args = @($Crate, "--locked", "--version", $Version.TrimStart('v'))
  }
  & cargo install @args
  if ($LASTEXITCODE -ne 0) { return $false }

  # cargo installs to $CARGO_HOME/bin; copy to $InstallDir if different
  $cargoExe = Join-Path (
    if ($env:CARGO_HOME) { $env:CARGO_HOME } else { Join-Path $HOME ".cargo" }
  ) "bin\$Binary.exe"
  if ((Resolve-Path $cargoExe).Path -ne (Join-Path $InstallDir "$Binary.exe")) {
    Copy-Item $cargoExe $InstallDir -Force
  }
  return $true
}

# ── PATH check ────────────────────────────────────────────────────────────
function Assert-Path {
  $pathDirs = $env:PATH -split ';'
  if ($InstallDir -notin $pathDirs) {
    Write-Warning "  ! $InstallDir is not in PATH."
    Write-Host "    To fix permanently, run:"
    Write-Host "    [Environment]::SetEnvironmentVariable('PATH', `$env:PATH + ';$InstallDir', 'User')"
  }
}

# ── Main ──────────────────────────────────────────────────────────────────
$arch = Get-Arch
$installed = $false

# Try prebuilt if arch is known and has a release asset
if ($arch -in @("amd64")) {
  # arm64 Windows: no prebuilt yet — skip straight to cargo
  $urls = Get-AssetUrl -Arch $arch -Ver $Version
  $installed = Install-Prebuilt -Urls $urls
}

if (-not $installed) {
  $installed = Install-ViaCargo
}

if (-not $installed) {
  Write-Error "  ✗ Installation failed. See messages above."
  exit 1
}

$ver = & (Join-Path $InstallDir "$Binary.exe") --version 2>$null
Write-Host "  ✓ Installed: $ver"
Assert-Path
```

---

## 7. Integration with Dotfile Setup Scripts

### 7.1 Caller pattern (existing `setup/common.sh`)

```bash
# In setup/common.sh — called by both setup.sh (macOS/Linux) and wsl-setup
install_agent_sync() {
  local version="${AGENT_SYNC_VERSION:-latest}"
  if command -v agent-sync >/dev/null 2>&1; then
    info "agent-sync already installed: $(agent-sync --version)"
    return 0
  fi
  info "Installing agent-sync $version …"
  # Download and pipe: this is safe because the script does its own checksum
  curl --proto '=https' --tlsv1.2 -fsSL \
    "https://raw.githubusercontent.com/OWNER/agent-sync/${version}/setup.sh" \
    | bash
}
```

### 7.2 Caller pattern (`setup.ps1`)

```powershell
# In setup.ps1 — Windows / WSL host
function Install-AgentSync {
  if (Get-Command agent-sync -ErrorAction SilentlyContinue) {
    Write-Host "agent-sync already installed: $(agent-sync --version)"
    return
  }
  $ver = $env:AGENT_SYNC_VERSION ?? "latest"
  $url = "https://raw.githubusercontent.com/OWNER/agent-sync/$ver/setup.ps1"
  # irm + iex is the idiomatic Windows one-liner; acceptable because our
  # setup.ps1 verifies the binary hash before installing.
  try {
    Invoke-Expression (Invoke-RestMethod $url)
  } catch {
    Write-Error "agent-sync install failed: $_"
  }
}
```

### 7.3 Deprecation of `bin/sync-ai-assistants`

`agent-sync sync` replaces the existing `bin/sync-ai-assistants` script.
Migration path:
1. Add `install_agent_sync` call early in `setup/common.sh`.
2. At the end of setup, replace `bin/sync-ai-assistants` call with `agent-sync sync`.
3. After cutover is confirmed, delete `bin/sync-ai-assistants` and add it to `.gitignore`.

---

## 8. Cargo Fallback Semantics

| Condition | Outcome |
|---|---|
| Prebuilt download succeeds + checksum OK | Installs prebuilt; fast path. |
| Prebuilt download returns HTTP 404 | Falls through to cargo. |
| Prebuilt download network error | Falls through to cargo. |
| Checksum mismatch | Hard abort; do **not** fall through. |
| Cargo available + prebuilt unavailable | `cargo install <crate> --locked` |
| Cargo unavailable + prebuilt unavailable | Print rustup URL; exit 1. |
| ARM Windows (no prebuilt) | Skip download attempt; cargo fallback directly. |
| 32-bit ARM Linux (armv7l) | Skip download attempt; cargo fallback directly. |

**Key invariant:** the fallback NEVER runs when the checksum fails.  
A tampered binary that fails verification causes a hard exit, not a source build.

---

## 9. Why Not cargo-binstall?

`cargo-binstall` is a popular alternative that queries crates.io, infers the
GitHub Release URL, and falls back to `cargo install`. Advantages:

- Zero setup for maintainers: just publish correctly-named assets.
- Handles `pkg.metadata.binstall` overrides in `Cargo.toml`.
- Users install with: `cargo binstall agent-sync`.

**Cons for a dotfiles bootstrap context:**
- Requires binstall itself to be installed first (chicken-and-egg on fresh machines).
- Adds a dependency the user might not have.
- Less transparent — harder to audit in a dotfiles setup script.

**Recommendation:** ship a self-contained `setup.sh`/`setup.ps1` AND document
`cargo binstall agent-sync` as an alternative for users who already have it.

---

## 10. Sources

1. GitHub Actions workflows reviewed: Terminus, fyi-cli, klaas, truffle, figctl (cross-rs blog)
2. cargo-dist v0.30.0 changelog — native arm64 runner switch (Sep 2025)
3. cargo-dist issue #2351 — prefer-binary-then-cargo fallback pattern
4. cargo-dist installer.ps1 source — arch detection via RuntimeInformation
5. goose `download_cli.sh` — WSL detection via `/proc/version`
6. Raspberry Pi rustup issues #3307, #3342, #3471 — 64-bit kernel / 32-bit userland confusion
7. cargo-binstall README — automatic binary inference from crates.io
8. SlanchaAi/wire PR #157 — hardened install.ps1 fallback for Windows ARM64
