<#
.SYNOPSIS
  PRE-GAME-LAUNCH ceremony: final checks before opening Victoria 3.
.DESCRIPTION
  ONE-COMMAND pre-game ritual run RIGHT BEFORE clicking "Play" in the launcher.
  Ensures a fresh, clean test environment every time.

  Performs (in order):
    1. Confirm versiontest mode is armed (must have run predev_preflight first)
    2. Clear all Vic3 logs (so error.log shows ONLY this run's issues)
    3. Optionally archive old logs for later inspection (use -Archive)

  CRITICAL: This is NOT predev_preflight. You must run predev_preflight ONCE per
  dev branch to enable debugging + stamp the build. This script runs EVERY TIME
  before launching the game.

  Workflow:
    1. (Once at branch start)   powershell -ExecutionPolicy Bypass -File scripts\predev_preflight.ps1 -Note "my message"
    2. (Every game launch)      powershell -ExecutionPolicy Bypass -File scripts\envSetup_pre_game_launch.ps1
    3. (In Vic3 launcher)       Click Play

.PARAMETER Archive
  Archive old logs to logs\_archive\<timestamp>\ before clearing (optional safeguard).
.PARAMETER Worktree
  Which worktree's versiontestMod to bump (default 'mod1' = master baseline). For a mod under active
  development in its own worktree, pass that worktree (e.g. 'mod1-inov') so the build stamp bumped is
  the one whose junction the launcher actually loads.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\envSetup_pre_game_launch.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\envSetup_pre_game_launch.ps1 -Archive
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\envSetup_pre_game_launch.ps1 -Worktree mod1-inov
#>
[CmdletBinding()]
param(
    [switch]$Archive,
    # Which worktree's versiontestMod build stamp to bump. Default 'mod1' (the master baseline).
    # Pass an active-dev worktree (e.g. 'mod1-inov') so the day-1 popup reflects THAT build under test.
    # Accepts -Worktree mod1-inov, a bare positional (mod1-inov), or a bare flag (--mod1-inov / -mod1-inov).
    [Parameter(Position = 0)]
    [string]$Worktree = 'mod1',
    # Catch a worktree passed as a bare flag (e.g. --mod1-inov) that PowerShell would otherwise
    # reject as an unknown parameter. The leading dashes are stripped below.
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = 'Stop'

# Normalise the worktree selector: a bare flag (--mod1-inov) lands in $Rest; strip leading dashes
# and let it override the default. Also strip dashes off an explicit -Worktree value just in case.
foreach ($a in $Rest) {
    $cand = ($a -replace '^-+', '').Trim()
    if ($cand) { $Worktree = $cand }
}
$Worktree = ($Worktree -replace '^-+', '').Trim()

Write-Host "=== PRE-GAME-LAUNCH ceremony ===" -ForegroundColor Cyan

# Resolve the logs directory (Documents is OneDrive-redirected on this machine)
$docs = [Environment]::GetFolderPath('MyDocuments')
$LogsDir = Join-Path $docs 'Paradox Interactive\Victoria 3\logs'

if (-not (Test-Path $LogsDir)) {
    Write-Host "ERROR: Vic3 logs dir not found at $LogsDir" -ForegroundColor Red
    Write-Host "Confirm Victoria 3 is installed and has been launched at least once."
    exit 1
}

Write-Host "  logs directory: $LogsDir" -ForegroundColor Gray

# Check if versiontest is armed (look for the build stamp in the loc file).
# repo root = two levels up from this script: hk-config\<scripts|tools> -> hk-config -> victoria-3-mod
# (works whether this script lives in scripts\ or tools\; both are one level under hk-config).
$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$locRel = 'versiontestMod\localization\english\versiontest_l_english.yml'
$versiontestLoc = Join-Path $repoRoot (Join-Path $Worktree $locRel)
Write-Host "  versiontest worktree: $Worktree" -ForegroundColor Gray

# If the chosen worktree has no versiontest loc, auto-discover which sibling worktrees do, so the
# user gets an actionable list instead of a silent fall-through onto the wrong (default) build stamp.
if (-not (Test-Path $versiontestLoc)) {
    $candidates = Get-ChildItem -Path $repoRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-Path (Join-Path $_.FullName $locRel) } |
        Select-Object -ExpandProperty Name
    Write-Host "  [!] no versiontest loc under worktree '$Worktree'" -ForegroundColor Yellow
    Write-Host "      looked for: $versiontestLoc" -ForegroundColor Gray
    if ($candidates) {
        Write-Host "      worktrees that DO have it: $($candidates -join ', ')" -ForegroundColor Gray
    }
    exit 1
}
if (Test-Path $versiontestLoc) {
    $content = Get-Content $versiontestLoc -Raw
    if ($content -match 'VTEST_BUILD \d{8,}') {
        Write-Host "  [OK] versiontest armed (marker found)" -ForegroundColor Green
    } else {
        Write-Host "  [!] versiontest marker not found - have you run predev_preflight?" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [!] versiontest loc file not found (new install?)" -ForegroundColor Yellow
}

# Bump the per-launch BUILD timestamp (yyyyMMddHHmm, pure digits, no separators) so the day-1
# popup + VTEST_BUILD marker show a FRESH, monotonically-higher value EVERY launch. Testbook
# VT-FRESH compares latest > last = a fresh build loaded, not a stale cache. Only the digit run
# is replaced here; predev_preflight owns the (branch) note context + the mod semver bump.
if (Test-Path $versiontestLoc) {
    $ts  = Get-Date -Format 'yyyyMMddHHmm'
    $raw = [System.IO.File]::ReadAllText($versiontestLoc)
    $raw = [regex]::Replace($raw, '(?m)(versiontest\.1\.d:0\s*"BUILD\s+)\d{8,}',     ('${1}' + $ts))
    $raw = [regex]::Replace($raw, '(?m)(versiontest_log:0\s*"VTEST_BUILD\s+)\d{8,}', ('${1}' + $ts))
    $utf8bom = New-Object System.Text.UTF8Encoding($true)   # loc files keep a UTF-8 BOM
    [System.IO.File]::WriteAllText($versiontestLoc, $raw, $utf8bom)
    Write-Host "  build timestamp -> $ts" -ForegroundColor Green
}

# Archive old logs if requested
if ($Archive) {
    $logs = Get-ChildItem -Path $LogsDir -Filter *.log -File -ErrorAction SilentlyContinue
    if ($logs) {
        $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
        $archivePath = Join-Path $LogsDir "_archive\$stamp"
        New-Item -ItemType Directory -Force $archivePath | Out-Null
        foreach ($f in $logs) {
            Copy-Item $f.FullName (Join-Path $archivePath $f.Name) -Force
        }
        Write-Host "  archived $($logs.Count) log(s) -> $archivePath" -ForegroundColor Gray
    }
}

# Clear logs (the main event)
$logs = Get-ChildItem -Path $LogsDir -Filter *.log -File -ErrorAction SilentlyContinue
if ($logs) {
    $cleared = 0
    foreach ($f in $logs) {
        try {
            Clear-Content -Path $f.FullName -ErrorAction Stop
            $cleared++
        } catch {
            Write-Host "  [!] Could not clear $($f.Name): $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
    Write-Host "  cleared $cleared/$($logs.Count) log file(s)" -ForegroundColor Green
} else {
    Write-Host "  (no .log files to clear - already clean)" -ForegroundColor Gray
}

Write-Host "=== ready to launch Victoria 3 ===" -ForegroundColor Green
