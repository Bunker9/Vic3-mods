<#
.SYNOPSIS
  Re-apply the Vic3 git baseline (IDEMPOTENT, WRITE script). Safe to re-run.
  Companion to the READ-ONLY githk_baseline_audit.ps1 - audit diagnoses, restore repairs.

.DESCRIPTION
  Applies the VIC3-SIDE baseline so the audit's Table-1 git checks pass:
    - mod1 local identity = the Vic3 account (HershGord)   [--local only; never global]
    - mod1 local credential helper = the gh helper          [reset to gh only]
    - origin remote URL pinned with the Vic3 username       [gh resolves it; default stays active]
  Then verifies via a read-only ls-remote.

  It DELIBERATELY does NOT (these are interactive / cross-account / human-only - it only PRINTS them):
    - touch the DEFAULT account's GCM bare credential (git:https://github.com)
    - run `gh auth login` / `gh auth switch`
    - *** NEVER runs `gh auth setup-git` *** (that is what clobbered the bare cred in the first place)
    - edit global/system git config

  Values come from hk-config/config/gitidentity.json (gitignored).

.PARAMETER WhatIf
  Print the actions without performing the writes.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File hk-config\scripts\githk_baseline_restore.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File hk-config\scripts\githk_baseline_restore.ps1 -WhatIf
#>
[CmdletBinding()]
param([switch]$WhatIf)
$ErrorActionPreference = 'Stop'

$scripts   = $PSScriptRoot
$hk        = Split-Path $scripts -Parent
$container = Split-Path $hk -Parent
$mod1      = Join-Path $container 'mod1'
$cfgPath   = Join-Path $hk 'config\gitidentity.json'

if (-not (Test-Path $cfgPath)) { Write-Host "ERROR: $cfgPath not found (copy from gitidentity.example.json)" -ForegroundColor Red; exit 1 }
$cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json

$vName   = $cfg.vic3_local.name
$vEmail  = $cfg.vic3_local.email
$vHelper = $cfg.vic3_local.helper
$remote  = $cfg.vic3_local.remote_url
$bareUsr = $cfg.windows_credentials.bare_host_user

Write-Host "=== Vic3 git baseline restore $(if($WhatIf){'(WhatIf - no writes)'})  ===" -ForegroundColor Cyan
if (-not (Test-Path (Join-Path $mod1 '.git'))) { Write-Host "ERROR: mod1\.git not found at $mod1" -ForegroundColor Red; exit 1 }

function Do-Git([string]$desc, [string[]]$gitArgs) {
  Write-Host "  $desc" -ForegroundColor Gray
  Write-Host "    git $($gitArgs -join ' ')"
  if (-not $WhatIf) { & git @gitArgs | Out-Null }
}

# 1. local identity (NEVER global)
Do-Git "local identity -> $vName" @('-C', $mod1, 'config', '--local', 'user.name', $vName)
Do-Git "local email -> $vEmail"   @('-C', $mod1, 'config', '--local', 'user.email', $vEmail)

# 2. credential: inherit system GCM ('manager') + repo-scoped PAT auth mode (never affects Karen)
Write-Host "  credential.helper -> inherit system GCM (manager); gitHubAuthModes -> pat (repo-scoped)" -ForegroundColor Gray
if (-not $WhatIf) {
  & git -C $mod1 config --local --unset-all credential.helper 2>$null | Out-Null   # drop any local override -> inherit system manager
  & git -C $mod1 config --local credential.gitHubAuthModes pat | Out-Null
} else {
  Write-Host "    git -C <mod1> config --local --unset-all credential.helper   # inherit system manager (GCM)"
  Write-Host "    git -C <mod1> config --local credential.gitHubAuthModes pat"
}

# 3. pin the remote URL with the Vic3 username
Do-Git "origin URL -> $remote" @('-C', $mod1, 'remote', 'set-url', 'origin', $remote)

# 4. verify WRITE-auth (push --dry-run is the real test; ls-remote is anonymous on a public repo).
Write-Host ""
if (-not $WhatIf) {
  $env:GIT_TERMINAL_PROMPT = '0'
  & git -C $mod1 push --dry-run 2>&1 | Out-Null
  if ($LASTEXITCODE -eq 0) { Write-Host "  [OK] write-auth verified (push --dry-run succeeded as $vName)" -ForegroundColor Green }
  else { Write-Host "  [WARN] push --dry-run failed (exit $LASTEXITCODE) - PAT not cached yet; run one real 'git push' (GCM stores it)" -ForegroundColor Yellow }
}

# 5. PRINT the human-only / cross-account steps (NEVER run here)
Write-Host ""
Write-Host "=== MANUAL steps (run YOURSELF - this script will not) ===" -ForegroundColor Yellow
Write-Host "  Default-account (e.g. XplanMagic) bare credential, if the audit flags it CLOBBERED:" -ForegroundColor Yellow
Write-Host "    1) cmdkey /delete:LegacyGeneric:target=git:https://github.com"
Write-Host "    2) trigger a push from a DEFAULT-account repo so GCM re-prompts and re-stores '$bareUsr'"
Write-Host "    (do NOT run 'gh auth setup-git' globally - that re-clobbers the bare cred)"
Write-Host ""
Write-Host "  Then verify everything: scripts\githk_baseline_audit.ps1  (aim: ALL PASS)" -ForegroundColor Gray
