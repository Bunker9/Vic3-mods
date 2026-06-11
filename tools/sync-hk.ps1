<#
sync-hk.ps1 — Refresh the hk/config housekeeping branch and push it.

Copies the container's project docs + tooling into the hk-config worktree, ENCRYPTS the
*.md notes via the age vault (hkvault seal), commits the non-secret rest, and pushes.

hk/config is an ORPHAN branch (no shared history with master), for disaster recovery /
new-machine bootstrap. NEVER merged to master.

Self-locating (no hardcoded user path) — run from the container's tools\ folder:
   powershell -ExecutionPolicy Bypass -File tools\sync-hk.ps1
#>
$ErrorActionPreference = "Stop"

# this script lives in <container>\tools\  ->  container root is its parent
$root = Split-Path $PSScriptRoot -Parent
$hk   = Join-Path $root "hk-config"

if (-not (Test-Path $hk)) {
    throw "hk-config worktree not found at $hk`nRecreate: git -C `"$root\mod1`" worktree add `"$hk`" hk/config"
}

foreach ($d in @("config", "docs", "tools")) {
    $p = Join-Path $hk $d
    if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
}

# NOTE: machine-specific editor config (.vscode\settings.json, *.code-workspace) is
# deliberately NOT copied here — it carries absolute C:\Users\<you> paths (PII) and would
# re-leak the username into git. Keep those locally; the committed de-usernamed snapshots
# under config\ are reference only.

# project .md docs (container root + roadmap) — these are SECRET; the age vault encrypts them
Copy-Item "$root\*.md"         "$hk\docs\" -Force -ErrorAction SilentlyContinue
Copy-Item "$root\roadmap\*.md" "$hk\docs\" -Force -ErrorAction SilentlyContinue

# tooling scripts + generated data (non-secret)
Copy-Item "$root\tools\*.py"  "$hk\tools\" -Force -ErrorAction SilentlyContinue
Copy-Item "$root\tools\*.ps1" "$hk\tools\" -Force -ErrorAction SilentlyContinue
Copy-Item "$root\tools\*.csv" "$hk\tools\" -Force -ErrorAction SilentlyContinue

Push-Location $hk
try {
    # 1) encrypt + commit any changed *.md notes (plaintext *.md is gitignored, never committed)
    python (Join-Path $hk "bin\hkvault.py") seal

    # 2) stage + commit the non-secret changes (csv, py, ps1, config, etc.); *.md stay ignored
    git add -A | Out-Null
    $changes = git status --porcelain
    if (-not [string]::IsNullOrWhiteSpace($changes)) {
        $stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
        git commit -m "hk: sync tooling/data snapshots ($stamp)" | Out-Null
    }

    # 3) push (seal commits locally but does not push)
    git push | Out-Null
    Write-Host "hk/config synced, sealed, and pushed." -ForegroundColor Green
    git --no-pager log -1 --oneline
}
finally {
    Pop-Location
}
