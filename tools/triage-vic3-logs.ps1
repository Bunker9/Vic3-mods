<#
.DEPRECATED (2026-06-10)
  SUPERSEDED by the Python test framework (sanity-check\testkit\run_test.py + checks\
  log_triage.py), which produces the tabbed HTML report. Kept for reference only; to be
  archived to the hk branch with a deprecation note. Do not extend this file.

.SYNOPSIS
  Post-test triage of Victoria 3 logs for Top40EcoBoostMod runs.
.DESCRIPTION
  Parses the Vic3 debug.log + error.log after an in-game test and produces a report:
    1. BUILD CENSUS  — per building: how many levels the eco engine placed, by type
       (champ/support/flavour), parsed from the "ECO_PLACED <type>" markers that follow
       each building-name header (debug_log = $B$). Verifies against expected caps.
    2. REAL ERRORS   — error.log with our own known-benign lines filtered out, so genuine
       failures (missing buildings, bad tokens, failed modifiers, crashes) stand out.
    3. SUMMARY        — counts + a pass/fail-ish read.

  Writes a timestamped markdown report to sanity-check\reports\ and prints a summary.

  This is the test/report side of the project (sanity-check\). Mod-design data analysis
  and housekeeping scripts live in tools\.

  Documents is OneDrive-redirected on this machine -> logs dir resolved via
  GetFolderPath('MyDocuments').
.PARAMETER LogsDir
  Override the Vic3 logs folder (default: resolved from MyDocuments).
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File sanity-check\triage-vic3-logs.ps1
#>
[CmdletBinding()]
param([string]$LogsDir)

$ErrorActionPreference = 'Stop'

if (-not $LogsDir) {
    $docs    = [Environment]::GetFolderPath('MyDocuments')
    $LogsDir = Join-Path $docs 'Paradox Interactive\Victoria 3\logs'
}
$debugLog = Join-Path $LogsDir 'debug.log'
$errorLog = Join-Path $LogsDir 'error.log'
$gameLog  = Join-Path $LogsDir 'game.log'
if (-not (Test-Path $debugLog)) { Write-Error "debug.log not found at $LogsDir"; exit 1 }

# ---- expected caps (mirror eco_effects.txt config) --------------------------
$expected = @{
    'Cotton Plantations'  = @{type='champ';   n=10}
    'Opium Plantations'   = @{type='support'; n=5}
    'Sugar Plantations'   = @{type='support'; n=5}
    'Tea Plantations'     = @{type='support'; n=5}
    'Textile Mills'       = @{type='support'; n=5}
    'Artillery Foundry'   = @{type='flavour'; n=1}
    'Paper Mills'         = @{type='flavour'; n=1}
    'Coffee Plantations'  = @{type='flavour'; n=1}
    'Tooling Workshops'   = @{type='flavour'; n=1}
    'Iron Mines'          = @{type='flavour'; n=1}
    'Logging Camps'       = @{type='flavour'; n=1}
    'Steel Mills'         = @{type='champ';   n=14}
    'Explosives Factory'  = @{type='support'; n=7}
    'Fertilizer Plants'   = @{type='support'; n=7}   # = chemical_plant display name
    'Motor Industries'    = @{type='support'; n=7}
}

# ---- 1. BUILD CENSUS --------------------------------------------------------
# eco debug_log lines surface as: ...eco_effects.txt:<line>: <payload>
# payload "ECO_PLACED <type>" = a placement marker; any other payload = building header.
$census = [System.Collections.Generic.List[object]]::new()
$current = $null
$rx = [regex]'eco_effects\.txt:\d+:\s*(?<p>.+?)\s*$'

foreach ($line in Get-Content $debugLog) {
    $m = $rx.Match($line)
    if (-not $m.Success) { continue }
    $p = $m.Groups['p'].Value
    if ($p -match '^ECO_PLACED\s+(\w+)') {
        if ($current) { $current.Count++ ; $current.Type = $matches[1] }
    }
    elseif ($p.Length -gt 0) {
        $current = [pscustomobject]@{ Building=$p; Type='?'; Count=0 }
        $census.Add($current)
    }
}

# ---- 2. REAL ERRORS (filter our known-benign noise) -------------------------
$benign = @(
    'should be in utf8-bom encoding',
    "loc string 'eco_log_",            # legacy, removed
    "for 'ROOT.GetName'",              # legacy, removed
    "for 'SCOPE.GetName'"              # legacy, removed
)
$realErrors = @()
if (Test-Path $errorLog) {
    $realErrors = Get-Content $errorLog | Where-Object {
        $l = $_; $l.Trim() -and -not ($benign | Where-Object { $l -like "*$_*" })
    }
}
# Match only OUR mod's files / identifiers (not generic words like "building"/"steel"
# that appear in vanilla game-state warnings, e.g. the Natalia barracks-cap message).
$modSig = 'eco_effects|eco_events|eco_on_actions|eco_modifiers|eco_target|eco_l_english|' +
          'eco_hit|eco_seed|eco_setup|eco_PAN|eco_PRU|eco_champ|eco_best|eco_placed|' +
          'diplo_test|punjab_sindh|sindh_pan_claim|diplo_infamy|versiontest'
$ecoErrors = $realErrors | Where-Object { $_ -match $modSig }

# ---- 3. write report --------------------------------------------------------
$stamp     = Get-Date -Format 'yyyyMMdd_HHmmss'
$reportDir = Join-Path $PSScriptRoot 'reports'
New-Item -ItemType Directory -Force $reportDir | Out-Null
$report    = Join-Path $reportDir "triage_$stamp.md"

$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# Vic3 EcoBoost triage - $stamp")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("Logs: ``$LogsDir``")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("## Build census (placed vs expected cap)")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("| Building | Type | Placed | Expected | OK |")
[void]$sb.AppendLine("|---|---|---:|---:|:--:|")
foreach ($row in $census) {
    $exp = $expected[$row.Building]
    $en  = if ($exp) { $exp.n } else { '?' }
    $ok  = if ($exp -and $row.Count -eq $exp.n) { 'YES' } elseif ($exp) { 'NO' } else { '—' }
    [void]$sb.AppendLine("| $($row.Building) | $($row.Type) | $($row.Count) | $en | $ok |")
}
[void]$sb.AppendLine("")
$byType = $census | Group-Object Type | ForEach-Object { "$($_.Name)=$([int]($_.Group | Measure-Object Count -Sum).Sum)" }
[void]$sb.AppendLine("Total levels placed by type: $($byType -join '  ')")
[void]$sb.AppendLine("")
[void]$sb.AppendLine("## Real errors (eco-related, benign filtered)")
[void]$sb.AppendLine("")
if ($ecoErrors) { $ecoErrors | ForEach-Object { [void]$sb.AppendLine("- ``$_``") } }
else            { [void]$sb.AppendLine("_None._ :tada:") }
[void]$sb.AppendLine("")
[void]$sb.AppendLine("## Error.log summary")
$total = if (Test-Path $errorLog) { (Get-Content $errorLog | Measure-Object -Line).Lines } else { 0 }
[void]$sb.AppendLine("- total lines: $total")
[void]$sb.AppendLine("- real (filtered) lines: $($realErrors.Count)")
[void]$sb.AppendLine("- eco-related real lines: $(@($ecoErrors).Count)")

Set-Content -Path $report -Value $sb.ToString() -Encoding UTF8

# ---- console summary --------------------------------------------------------
Write-Host ""
Write-Host "=== BUILD CENSUS ===" -ForegroundColor Cyan
$census | ForEach-Object {
    $exp = $expected[$_.Building]; $en = if ($exp){$exp.n}else{'?'}
    $flag = if ($exp -and $_.Count -eq $exp.n){'OK '} elseif($exp){'<<<'} else {'   '}
    "{0,4} {1,-22} {2,3}/{3,-3} {4}" -f $flag, $_.Building, $_.Count, $en, $_.Type
}
Write-Host ""
Write-Host "Totals: $($byType -join '  ')" -ForegroundColor Cyan
Write-Host ""
if ($ecoErrors) {
    Write-Host "=== ECO-RELATED REAL ERRORS ($(@($ecoErrors).Count)) ===" -ForegroundColor Yellow
    $ecoErrors | Select-Object -First 25 | ForEach-Object { Write-Host "  $_" }
} else {
    Write-Host "No eco-related real errors." -ForegroundColor Green
}
Write-Host ""
Write-Host "Report saved: $report" -ForegroundColor Green
