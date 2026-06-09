<#
sync-hk.ps1 — Refresh the hk/config housekeeping branch and push it.

Copies the current tool settings, project .md docs, and tooling scripts into the
hk/config worktree, then commits + pushes (only if something changed).

The hk/config branch is an ORPHAN branch (no shared history with master) used purely
for disaster recovery / new-machine bootstrap. NEVER merged to master.

Usage:   powershell -ExecutionPolicy Bypass -File tools\sync-hk.ps1
#>
$ErrorActionPreference = "Stop"

$root = "C:\Users\user\Projects\victoria-3-mod"
$hk   = Join-Path $root "hk-config"

if (-not (Test-Path $hk)) {
    throw "hk-config worktree not found at $hk`nRecreate it with: git -C `"$root\mod1`" worktree add `"$hk`" hk/config"
}

# --- ensure target subfolders exist ---
foreach ($d in @("config", "docs", "tools")) {
    $p = Join-Path $hk $d
    if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
}

# --- config / editor / tool settings ---
Copy-Item "$root\mod1\Top40EcoBoostMod\.vscode\settings.json" "$hk\config\vscode-settings.json" -Force
Copy-Item "$root\Top40EcoBoostMod.code-workspace"             "$hk\config\"                      -Force
Copy-Item "$root\mod1\TODO-CI.md"                             "$hk\config\"                      -Force

# --- all project .md docs (container root + roadmap) — auto-captures new md files ---
Copy-Item "$root\*.md"          "$hk\docs\" -Force
Copy-Item "$root\roadmap\*.md"  "$hk\docs\" -Force

# --- tooling scripts + generated data (everything in tools/) ---
Copy-Item "$root\tools\*.py"  "$hk\tools\" -Force
Copy-Item "$root\tools\*.ps1" "$hk\tools\" -Force
Copy-Item "$root\tools\*.csv" "$hk\tools\" -Force -ErrorAction SilentlyContinue

# --- commit + push only if there are changes ---
Push-Location $hk
try {
    git add -A | Out-Null
    $changes = git status --porcelain
    if ([string]::IsNullOrWhiteSpace($changes)) {
        Write-Host "hk/config already up to date - nothing to sync." -ForegroundColor Green
    } else {
        $stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
        git commit -m "hk: sync config/doc snapshots ($stamp)" | Out-Null
        git push | Out-Null
        Write-Host "hk/config synced and pushed:" -ForegroundColor Green
        git --no-pager log -1 --oneline
    }
}
finally {
    Pop-Location
}
