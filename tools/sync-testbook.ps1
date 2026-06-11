<#
sync-testbook.ps1 - Archive the current test artifacts to the orphan `testbook` branch.

For each tested mod it copies that mod's test artifacts (report + bdd/observe/props/static)
into testbook\<ModName>\, records when/what commit it was tested at, regenerates a
recency-ordered INDEX.md (most-recently-tested mod on top), then commits + pushes.

`testbook` is an ORPHAN branch (no shared history with master) - like hk/config, it is NEVER
merged to master. Provenance (which code commit each archive validated) lives in the testbook
COMMIT MESSAGE; formal correlated markers across code+testbook+hkconfig are the job of
checkpoints (tools\checkpoint.ps1), so this script no longer creates per-sync tags.

Usage:
  powershell -ExecutionPolicy Bypass -File tools\sync-testbook.ps1            # all tested mods
  powershell -ExecutionPolicy Bypass -File tools\sync-testbook.ps1 Top40EcoBoostMod
#>
[CmdletBinding()]
param([string[]]$Mods)

$ErrorActionPreference = "Stop"
$root    = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent   # <container>\hk-config\tools -> container
$sanity  = Join-Path $root "sanity-check"
$tb      = Join-Path $root "testbook"
$mod1    = Join-Path $root "mod1"

if (-not (Test-Path $tb)) {
    throw "testbook worktree not found at $tb`nRecreate: git -C `"$mod1`" worktree add --orphan -b testbook `"$tb`""
}

# tested commit + branch (from the mod repo)
$commit = (& git -C $mod1 rev-parse --short HEAD).Trim()
$branch = (& git -C $mod1 rev-parse --abbrev-ref HEAD).Trim()
$date   = Get-Date -Format "yyyy-MM-dd HH:mm"
$day    = Get-Date -Format "yyyy-MM-dd"

# which mods: arg list, else every test-<Mod> folder that has a props.toml
if (-not $Mods) {
    $Mods = Get-ChildItem $sanity -Directory -Filter "test-*" |
            Where-Object { Test-Path (Join-Path $_.FullName "props.toml") } |
            ForEach-Object { $_.Name -replace '^test-', '' }
}

# the shared report for this branch
$report = Join-Path $sanity ("{0}.html" -f ($branch -replace '/', '-'))

function Get-BddSummary($bddPath) {
    if (-not (Test-Path $bddPath)) { return "n/a" }
    $p = 0; $f = 0; $na = 0
    foreach ($ln in Get-Content $bddPath) {
        if ($ln -notmatch '^\s*\|') { continue }
        $c = ($ln -replace '^\s*\|','' -replace '\|\s*$','') -split '\|' | ForEach-Object { $_.Trim() }
        if ($c.Count -lt 5 -or $c[0] -eq '#' -or $c[0] -match '^[-: ]+$') { continue }
        $exp = if ($c[2] -match '^(Y|YES)$') {'Y'} elseif ($c[2] -match '^(N|NO)$') {'N'} else {''}
        $ans = if ($c[3] -match '^(Y|YES)$') {'Y'} elseif ($c[3] -match '^(N|NO)$') {'N'} else {''}
        if (-not $ans) { $na++ } elseif ($ans -eq $exp) { $p++ } else { $f++ }
    }
    "$p PASS / $f FAIL / $na NA"
}

foreach ($m in $Mods) {
    $src = Join-Path $sanity "test-$m"
    if (-not (Test-Path $src)) { Write-Warning "no test-$m in sanity-check - skipping"; continue }
    $dst = Join-Path $tb $m
    New-Item -ItemType Directory -Force $dst | Out-Null
    foreach ($f in @("bdd.md","observe.md","props.toml","static.json")) {
        $sp = Join-Path $src $f
        if (Test-Path $sp) { Copy-Item $sp $dst -Force }
    }
    if (Test-Path $report) { Copy-Item $report (Join-Path $dst "report.html") -Force }
    $bdd = Get-BddSummary (Join-Path $src "bdd.md")
    @"
tested: $date
branch: $branch
commit: $commit
bdd:    $bdd
"@ | Set-Content -Path (Join-Path $dst "_meta.txt") -Encoding utf8
}

# regenerate INDEX.md - mods sorted by last-tested date, newest on top
$rows = Get-ChildItem $tb -Directory | Where-Object { Test-Path (Join-Path $_.FullName "_meta.txt") } |
    ForEach-Object {
        $meta = Get-Content (Join-Path $_.FullName "_meta.txt") -Raw
        $get  = { param($k) ([regex]::Match($meta, "$k`:\s*(.+)")).Groups[1].Value.Trim() }
        [pscustomobject]@{
            Mod = $_.Name; Tested = (& $get 'tested'); Branch = (& $get 'branch')
            Commit = (& $get 'commit'); Bdd = (& $get 'bdd')
        }
    } | Sort-Object Tested -Descending

$idx = @("# Testbook - archived test runs", "",
         "Orphan branch (never merged to master). Most-recently-tested mod on top.", "",
         "| Mod | Last tested | Branch | Commit | BDD |", "|---|---|---|---|---|")
$idx += $rows | ForEach-Object { "| [$($_.Mod)]($($_.Mod)/report.html) | $($_.Tested) | $($_.Branch) | ``$($_.Commit)`` | $($_.Bdd) |" }
$idx -join "`n" | Set-Content -Path (Join-Path $tb "INDEX.md") -Encoding utf8

# .gitignore (hygiene - never archive python cruft)
"__pycache__/`n*.pyc`n" | Set-Content -Path (Join-Path $tb ".gitignore") -Encoding utf8

# commit + push (provenance = the commit message; correlated markers = checkpoints)
Push-Location $tb
try {
    git add -A | Out-Null
    if ([string]::IsNullOrWhiteSpace((git status --porcelain))) {
        Write-Host "testbook already up to date - nothing to sync." -ForegroundColor Green
    } else {
        git commit -m "testbook: $($Mods -join ', ') tested on $branch @ $commit ($date)" | Out-Null
        git push -u origin testbook | Out-Null
        Write-Host "testbook synced + pushed (commit records tested code @ $commit)." -ForegroundColor Green
        git --no-pager log -1 --oneline
    }
}
finally { Pop-Location }
