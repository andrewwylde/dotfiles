#Requires -Version 5.1
<#
.SYNOPSIS
  Windows host setup for WSL-based development with dotfiles.

.DESCRIPTION
  Prepares Windows for WSL2, installs recommended host tools, then tells you
  to run wsl-setup.sh inside Ubuntu. Dev tooling (git/zsh/rcup) lives in WSL,
  not on the Windows host.

.USAGE
  powershell -ExecutionPolicy Bypass -File .\setup.ps1
  ./setup.sh            # from Git Bash — delegates here

  Usually invoked via setup.ps1 or setup.sh, not directly.
#>

$ErrorActionPreference = 'Stop'

function Write-Info($Message) {
  Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-Warn($Message) {
  Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Test-Admin {
  $current = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
  return $current.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Ensure-Wsl {
  Write-Info 'Checking WSL...'

  $wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
  if (-not $wsl) {
    if (-not (Test-Admin)) {
      throw 'WSL is not installed. Re-run this script in an elevated PowerShell window.'
    }

    Write-Info 'Installing WSL with default Ubuntu distro...'
    wsl.exe --install
    Write-Warn 'Reboot if prompted, then open Ubuntu and complete distro first-run setup.'
    return
  }

  $status = wsl.exe --status 2>&1 | Out-String
  Write-Info "WSL status:`n$status"

  $distros = wsl.exe -l -v 2>&1 | Out-String
  if ($distros -notmatch 'Ubuntu') {
    Write-Warn 'Ubuntu not found. Install with: wsl.exe --install -d Ubuntu'
  } else {
    Write-Info "Installed distros:`n$distros"
  }

  wsl.exe --set-default-version 2 2>$null | Out-Null
}

function Install-WingetPackage($Id, $Name) {
  $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
  if (-not $winget) {
    Write-Warn "winget not found; skip installing $Name"
    return
  }

  Write-Info "Installing $Name ($Id)..."
  winget.exe install --id $Id -e --accept-source-agreements --accept-package-agreements 2>$null | Out-Null
}

function Install-HostTools {
  Write-Info 'Installing recommended Windows host tools (optional but useful)...'
  Install-WingetPackage 'Microsoft.WindowsTerminal' 'Windows Terminal'
  Install-WingetPackage 'Git.Git' 'Git for Windows'
  Install-WingetPackage 'Docker.DockerDesktop' 'Docker Desktop'
  Install-WingetPackage 'Anysphere.Cursor' 'Cursor'
}

function Show-WslBootstrapSteps {
  $repo = 'https://github.com/andrewwylde/dotfiles.git'

  Write-Host ''
  Write-Info 'Windows host prep is done (or WSL install was started).'
  Write-Host ''
  Write-Host 'Inside Ubuntu (WSL), run:' -ForegroundColor Cyan
  Write-Host @"

  git clone $repo ~/dotfiles
  cd ~/dotfiles
  ./wsl-setup.sh

"@ -ForegroundColor White
  Write-Host 'Then open your project from the WSL path in Cursor:' -ForegroundColor Cyan
  Write-Host '  \\wsl$\Ubuntu\home\<you>\...' -ForegroundColor White
  Write-Host ''
  Write-Warn 'Keep machine-specific config in ~/dotfiles-local/ inside WSL.'
}

function Main {
  Write-Info 'Starting Windows host setup for dotfiles + WSL...'

  if (-not (Test-Admin)) {
    Write-Warn 'Not running as Administrator. WSL install may fail; host tool installs via winget usually still work.'
  }

  Ensure-Wsl
  Install-HostTools
  Show-WslBootstrapSteps
}

Main
