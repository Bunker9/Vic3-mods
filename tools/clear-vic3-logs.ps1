<#
.SYNOPSIS
  Clear Victoria 3 log files before an in-game test run.
.DESCRIPTION
  Empties every *.log in the Vic3 logs folder so a fresh run's error.log shows ONLY the
  current build's issues (no re-reading stale errors). Part of the pre-test process,
  alongside enabling versiontestMod + bumping its build stamp.

  By default it truncates the logs in place (the game recreates content on next launch).
  With -Archive it first copies them to logs\_archive\<timestamp>\ so nothing is lost.

  Documents is OneDrive-redirected on this machine, so the path is resolved via
  GetFolderPath('MyDocuments') (NOT a literal ...\Documents\... path).
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\clear-vic3-logs.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\clear-vic3-logs.ps1 -Archive
#>
[CmdletBinding()]
param(
    [switch]$Archive,
    [string]$LogsDir
)

if (-not $LogsDir) {
    $docs = [Environment]::GetFolderPath('MyDocuments')   # resolves the OneDrive redirect
    $LogsDir = Join-Path $docs 'Paradox Interactive\Victoria 3\logs'
}

if (-not (Test-Path $LogsDir)) {
    Write-Error "Vic3 logs dir not found: $LogsDir"
    exit 1
}

$logs = Get-ChildItem -Path $LogsDir -Filter *.log -File -ErrorAction SilentlyContinue
if (-not $logs) {
    Write-Host "No .log files in $LogsDir (already clean)."
    exit 0
}

if ($Archive) {
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $dest  = Join-Path $LogsDir "_archive\$stamp"
    New-Item -ItemType Directory -Force $dest | Out-Null
    foreach ($f in $logs) { Copy-Item $f.FullName (Join-Path $dest $f.Name) }
    Write-Host "Archived $($logs.Count) log(s) -> $dest"
}

$cleared = 0
foreach ($f in $logs) {
    try { Clear-Content -Path $f.FullName -ErrorAction Stop; $cleared++ }
    catch { Write-Warning "Could not clear $($f.Name): $($_.Exception.Message)" }
}
Write-Host "Cleared $cleared/$($logs.Count) log file(s) in $LogsDir"
