#Requires -Version 5.1
<#
.SYNOPSIS
  Dotfiles setup router for Windows.

.DESCRIPTION
  Runs windows-setup.ps1 on the Windows host, then optionally bootstraps WSL
  via wsl-setup.sh inside your default Ubuntu distro.

.USAGE
  powershell -ExecutionPolicy Bypass -File .\setup.ps1

  From Git Bash you can also run: ./setup.sh
#>

$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WindowsSetup = Join-Path $ScriptDir 'windows-setup.ps1'
$WslSetup = Join-Path $ScriptDir 'wsl-setup.sh'

function Write-Info($Message) {
  Write-Host "[setup] $Message" -ForegroundColor Green
}

function Test-WslDistroReady {
  $list = wsl.exe -l -q 2>$null
  if ($LASTEXITCODE -ne 0 -or -not $list) {
    return $false
  }
  return ($list | Where-Object { $_ -match 'Ubuntu' }).Count -gt 0
}

function Invoke-WslSetup {
  if (-not (Test-Path $WslSetup)) {
    Write-Host "[setup] ERROR: missing $WslSetup" -ForegroundColor Red
    exit 1
  }

  if (-not (Test-WslDistroReady)) {
    Write-Host '[setup] Ubuntu WSL distro not ready yet — finish WSL first-run, then run:' -ForegroundColor Yellow
    Write-Host "  wsl -d Ubuntu -- bash -lc 'cd ~/dotfiles && ./wsl-setup.sh'" -ForegroundColor White
    return
  }

  $answer = Read-Host 'Run wsl-setup.sh inside Ubuntu now? (y/n)'
  if ($answer -notmatch '^[Yy]') {
    Write-Host '[setup] Skipped WSL bootstrap. Run later inside Ubuntu:' -ForegroundColor Yellow
    Write-Host "  git clone https://github.com/andrewwylde/dotfiles.git ~/dotfiles" -ForegroundColor White
    Write-Host '  cd ~/dotfiles && ./wsl-setup.sh' -ForegroundColor White
    return
  }

  Write-Info 'Running wsl-setup.sh in Ubuntu...'
  $cmd = @"
set -e
if [ ! -d ~/dotfiles/.git ]; then
  git clone https://github.com/andrewwylde/dotfiles.git ~/dotfiles
fi
cd ~/dotfiles
chmod +x wsl-setup.sh setup.sh
./wsl-setup.sh
"@

  wsl.exe -d Ubuntu -- bash -lc $cmd
}

if (-not (Test-Path $WindowsSetup)) {
  Write-Host "[setup] ERROR: missing $WindowsSetup" -ForegroundColor Red
  exit 1
}

Write-Info 'Windows detected — running windows-setup.ps1'
& $WindowsSetup
Invoke-WslSetup
