<#
.SYNOPSIS
  Encrypt data/TODO.xlsx -> data/TODO.xlsx.age (age, public-key) so it can be COMMITTED to the
  public repo while staying unreadable to anyone browsing GitHub. Plaintext TODO.xlsx stays gitignored
  + locally editable. Same vault key as the .md docs (bin/vault.pub / ~/.vic3-vault/identity.key).

.DESCRIPTION
  Default = SEAL (encrypt). Needs only the PUBLIC key (bin/vault.pub).
  -Unseal = decrypt the .age back to TODO.xlsx (needs the PRIVATE key; for recovery on a new machine).
  Run SEAL as part of the pre-push ceremony after updating TODO.xlsx.

  -Path <file> seals ANY binary that git ignores but must survive a re-clone (xlsx trackers,
  images). Path is relative to the hk-config root, or absolute. Defaults to data\TODO.xlsx.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File hk-config\tools\githk_seal_todo.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File hk-config\tools\githk_seal_todo.ps1 -Unseal
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File hk-config\tools\githk_seal_todo.ps1 -Path data\testbook_status.xlsx
#>
[CmdletBinding()]
param([switch]$Unseal, [string]$Path = 'data\TODO.xlsx')
$ErrorActionPreference = 'Stop'

$tools = $PSScriptRoot
$hk    = Split-Path $tools -Parent
$age   = Join-Path $hk 'bin\age.exe'
$pub   = Join-Path $hk 'bin\vault.pub'
$xlsx  = if (Split-Path -IsAbsolute $Path) { $Path } else { Join-Path $hk $Path }
$enc   = "$xlsx.age"
$rel   = $Path
$key   = Join-Path $env:USERPROFILE '.vic3-vault\identity.key'

if (-not (Test-Path $age)) { Write-Host "age.exe not found at $age" -ForegroundColor Red; exit 1 }

if ($Unseal) {
  if (-not (Test-Path $enc)) { Write-Host "no $enc to unseal" -ForegroundColor Yellow; exit 0 }
  if (-not (Test-Path $key)) { Write-Host "private key not found at $key (restore from DR email)" -ForegroundColor Red; exit 1 }
  & $age -d -i $key -o $xlsx $enc
  if ($LASTEXITCODE -eq 0) { Write-Host "unsealed -> $rel" -ForegroundColor Green } else { Write-Host "age decrypt failed" -ForegroundColor Red; exit 1 }
  exit 0
}

# SEAL (default)
if (-not (Test-Path $xlsx)) { Write-Host "no $rel to seal (nothing to do)" -ForegroundColor Yellow; exit 0 }
& $age -R $pub -o $enc $xlsx
if ($LASTEXITCODE -eq 0) {
  Write-Host "sealed $rel -> $rel.age (commit the .age; plaintext stays gitignored)" -ForegroundColor Green
  Write-Host "  remember to: git add `"$rel.age`""
} else { Write-Host "age encrypt failed" -ForegroundColor Red; exit 1 }
