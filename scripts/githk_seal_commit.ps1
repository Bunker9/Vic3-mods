<#
.SYNOPSIS
  One-click seal + commit for the hk-config vault (Pre-Push Ceremony 5, scripted).

  Encrypts the private plaintext notes (*.md -> *.md.age) and TODO.xlsx (-> .age), stages
  everything, and makes ONE local commit. Push stays manual (the no-push rule) unless -Push.

  Class: githk_  (git/vault housekeeping). Self-locating: run from anywhere.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File hk-config\scripts\githk_seal_commit.ps1 -Message "docs: naming conventions + v2 phase 2"

.PARAMETER Message   Commit message (required in spirit; a dated default is used if omitted).
.PARAMETER Push      Also push (you normally push from a real terminal; off by default).
#>
[CmdletBinding()]
param(
    [string]$Message = "vault: seal docs + tracker ($(Get-Date -Format 'yyyy-MM-dd HH:mm'))",
    [switch]$Push
)
$ErrorActionPreference = 'Stop'

# repo root = parent of tools/
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
Write-Host "hk-config root: $root" -ForegroundColor Cyan

# 1) seal the private *.md -> *.md.age (do not let hkvault self-commit; we commit once at the end)
Write-Host "Sealing notes (*.md -> *.md.age)..." -ForegroundColor Cyan
python bin\hkvault.py seal --no-commit
if ($LASTEXITCODE -ne 0) { throw "hkvault seal failed (exit $LASTEXITCODE)" }

# 2) seal the tracker TODO.xlsx -> .age (idempotent; skip if the script/file is absent)
if (Test-Path "tools\githk_seal_todo.ps1") {
    Write-Host "Sealing TODO.xlsx..." -ForegroundColor Cyan
    powershell -ExecutionPolicy Bypass -File "tools\githk_seal_todo.ps1"
}

# 3) stage everything (plaintext *.md / *.xlsx are gitignored -> only .age + scripts/configs land)
git add -A

# guard: never let plaintext private notes slip in
$staged = git diff --cached --name-only
$bad = $staged | Where-Object { $_ -match '\.md$' -and $_ -notmatch '(^|/)(README|CHECKPOINTS)\.md$' }
if ($bad) {
    Write-Host "ABORT: plaintext .md staged (should be .age only):" -ForegroundColor Red
    $bad | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    throw "refusing to commit plaintext notes"
}

if (-not $staged) { Write-Host "Nothing to commit." -ForegroundColor Yellow; return }

# 4) commit (no Co-Author trailer on the private vault, per Ceremony 5)
git commit -m $Message
Write-Host "Committed on hk/config." -ForegroundColor Green

if ($Push) {
    git push
} else {
    Write-Host "Not pushed. Push from a real terminal when ready:  git -C `"$root`" push" -ForegroundColor Yellow
}
