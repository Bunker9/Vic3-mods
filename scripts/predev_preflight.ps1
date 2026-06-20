<#
.SYNOPSIS
  ONE-COMMAND pre-development preflight for a Vic3 dev cycle. Run it after creating/checking out
  a dev branch, BEFORE writing mod code - so the in-game test bundle is correctly armed.

.DESCRIPTION
  Bundles the whole ritual (so we never hand-do it again - see memory `predev-preflight`):
    1. versiontestMod mode   -> ENABLED for the current dev/test branch (tools\set-versiontest-mode.ps1)
    2. versiontest marker     -> popup "BUILD <yyyyMMddHHmm>" + "VTEST_BUILD <ts> (branch) note";
                                  also bumps versiontestMod metadata semver (per-branch cache flush)
    3. debug_log statements  -> turned ON across all mods (tools\testbook_toggle_debuglog.py --on)
  Reverse it before promoting to master with  -Promote  (disable versiontest + debug_log OFF).

  Does NOT (these are launch-time / per-mod, not branch-arming):
    - clear Vic3 logs (do that right before launching: tools\clear-vic3-logs.ps1)
    - junction NEW mods to the launcher (do per new mod: tools\link-mod-to-launcher.ps1)

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\predev_preflight.ps1 -Note "dev/exp kickoff"
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\predev_preflight.ps1 -Promote   # pre-master
#>
[CmdletBinding()]
param(
  [string]$Branch,
  [string]$Note    = "",
  [string]$Version = "",          # optional version tag for the stamp, e.g. v0.3.0
  [switch]$Promote                 # reverse: disable versiontest + debug_log OFF (pre-master)
)
$ErrorActionPreference = 'Stop'
$scripts = $PSScriptRoot
$hk      = Split-Path $scripts -Parent
$tools   = Join-Path $hk 'tools'
$mod1    = Join-Path (Split-Path $hk -Parent) 'mod1'
if (-not $Branch) { $Branch = (& git -C $mod1 rev-parse --abbrev-ref HEAD).Trim() }

Write-Host "=== predev preflight  (branch '$Branch'$(if($Promote){' , PROMOTE/master mode'}))  ===" -ForegroundColor Cyan

# 1) versiontestMod mode from branch (set-versiontest-mode already disables on master)
$modeBranch = if ($Promote) { 'master' } else { $Branch }
& (Join-Path $tools 'set-versiontest-mode.ps1') -Branch $modeBranch

# 2) set the versiontest build marker (skip on promote: keep release stamp as-is).
#    in-game popup (.d) = clean "BUILD <yyyyMMddHHmm>" (no dashes/slashes - the player loc rule).
#    debug marker (versiontest_log) = "VTEST_BUILD <ts> (branch) note" (dashes/slashes OK - debug).
#    envSetup_pre_game_launch.ps1 then refreshes <ts> on EVERY launch; this sets the branch/note.
if (-not $Promote) {
  $loc  = Join-Path $mod1 'versiontestMod\localization\english\versiontest_l_english.yml'
  $ts   = Get-Date -Format 'yyyyMMddHHmm'
  $ctx  = "($Branch)"
  if ($Version) { $ctx += " $Version" }
  if ($Note)    { $ctx += " $Note" }
  $txt = [System.IO.File]::ReadAllText($loc)
  $txt = [regex]::Replace($txt, '(?m)^(\s*versiontest\.1\.d:0\s*)".*"\s*$', ('${1}"BUILD ' + $ts + '"'))
  $txt = [regex]::Replace($txt, '(?m)^(\s*versiontest_log:0\s*)".*"\s*$', ('${1}"VTEST_BUILD ' + $ts + ' ' + $ctx + '"'))
  $utf8bom = New-Object System.Text.UTF8Encoding($true)
  [System.IO.File]::WriteAllText($loc, $txt, $utf8bom)
  Write-Host "  build marker -> `"BUILD $ts`"  /  `"VTEST_BUILD $ts $ctx`""

  # 2b) bump versiontestMod metadata semver (patch) so Vic3 sees a fresh mod version on a new
  #     branch (cache flush). Maturity semver, per-branch ONLY (never per launch). metadata.json
  #     must NOT carry a BOM.
  $meta = Join-Path $mod1 'versiontestMod\.metadata\metadata.json'
  $mraw = [System.IO.File]::ReadAllText($meta)
  if ($mraw -match '"version"\s*:\s*"(\d+)\.(\d+)\.(\d+)"') {
    $bumped = "$($Matches[1]).$($Matches[2]).$([int]$Matches[3] + 1)"
    $mraw = [regex]::Replace($mraw, '("version"\s*:\s*")\d+\.\d+\.\d+(")', ('${1}' + $bumped + '${2}'))
    [System.IO.File]::WriteAllText($meta, $mraw, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "  versiontest metadata version -> $bumped"
  }
}

# 3) debug_log ON for dev/test  (OFF when promoting to master)
$dbgArg = if ($Promote) { '--off' } else { '--on' }
& python (Join-Path $tools 'testbook_toggle_debuglog.py') $dbgArg

Write-Host "=== preflight done ===" -ForegroundColor Green
if (-not $Promote) {
  Write-Host "  reminders: junction any NEW mod (tools\link-mod-to-launcher.ps1); clear logs before launch (tools\clear-vic3-logs.ps1)."
}
