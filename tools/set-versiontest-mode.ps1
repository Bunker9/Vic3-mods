<#
.SYNOPSIS
  Set versiontestMod's mode from the current git branch.
.DESCRIPTION
  versiontestMod is a TEST-ONLY load-confirmation popup. Its behaviour should track the
  branch it's on:
    - dev/*   -> ENABLED, popup option reads "DEV - read me"
    - test/*  -> ENABLED, popup option reads "TESTER - verify this build & sign off"
    - master  -> DISABLED (soft): the enable-gate trigger flips to `always = no`, so the
                 on_action never fires the popup in the released playset (mod not deleted).

  Edits two files (BOM preserved):
    mod1\versiontestMod\common\scripted_triggers\versiontest_triggers.txt   (always = yes/no)
    mod1\versiontestMod\localization\english\versiontest_l_english.yml       (versiontest.1.a)

  Run this when you switch the versiontestMod branch, and ALWAYS before promoting to master
  (so the popup is soft-disabled there). Safe to re-run / idempotent.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\set-versiontest-mode.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\set-versiontest-mode.ps1 -Branch master
#>
[CmdletBinding()]
param([string]$Branch)

$ErrorActionPreference = 'Stop'
$mod1 = Join-Path $PSScriptRoot '..\..\mod1'   # tools\ -> hk-config\ -> container -> mod1
if (-not $Branch) { $Branch = (& git -C $mod1 rev-parse --abbrev-ref HEAD).Trim() }

switch -Regex ($Branch) {
    '^master$|^main$' { $enabled = 'no';  $opt = '(versiontestMod is soft-disabled on master)' }
    '^test/'          { $enabled = 'yes'; $opt = 'TESTER - verify this build & sign off' }
    default           { $enabled = 'yes'; $opt = 'DEV - read me' }   # dev/*, hk/*, anything else
}

function Set-FileText([string]$path, [string]$pattern, [string]$replacement) {
    $raw = [System.IO.File]::ReadAllText($path)
    $new = [regex]::Replace($raw, $pattern, $replacement)
    $utf8bom = New-Object System.Text.UTF8Encoding($true)   # keep the BOM Vic3 wants
    [System.IO.File]::WriteAllText($path, $new, $utf8bom)
}

$trig = Join-Path $mod1 'versiontestMod\common\scripted_triggers\versiontest_triggers.txt'
$loc  = Join-Path $mod1 'versiontestMod\localization\english\versiontest_l_english.yml'

Set-FileText $trig '(?m)(always\s*=\s*)(yes|no)' ('${1}' + $enabled)
Set-FileText $loc  '(?m)^(\s*versiontest\.1\.a:0\s*)".*"\s*$' ('${1}"' + $opt + '"')
# keep the on-option debug_log string in sync (shows in the test report's "Load marker" table)
Set-FileText $loc  '(?m)^(\s*versiontest_log:0\s*)".*"\s*$' ('${1}"VTEST_LOG ' + $opt + '"')

Write-Host "versiontestMod mode set for branch '$Branch':  enabled=$enabled  option=`"$opt`""
