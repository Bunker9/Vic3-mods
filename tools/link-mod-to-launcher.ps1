<#
.SYNOPSIS
  Junction a mod from the repo (mod1\) into the Victoria 3 game mod folder so the
  launcher detects it.
.DESCRIPTION
  REQUIRED because the Vic3 launcher's custom mod-location setting is buggy on this
  machine: it appends a spurious "\victoria3" to whatever path you set, and editing
  the launcher sqlite by hand crashes the launcher. The tried-and-tested remedy is to
  leave the launcher pointed at its DEFAULT mod folder and place a directory JUNCTION
  there that points back at the repo copy under mod1\. The game then loads straight
  from the repo (hotload-from-repo) while the launcher stays happy.

  Idempotent: if a healthy junction already points at the right target it does nothing.
  If a STALE empty folder is sitting at the path (OneDrive sometimes materialises a new
  junction into an empty ReadOnly dir), it clears the ReadOnly attr and removes it first,
  then recreates the junction. It will NOT delete a non-empty real folder (safety).

  Documents is OneDrive-redirected on this machine, so the mod folder is resolved via
  GetFolderPath('MyDocuments') (NOT a literal ...\Documents\... path).
.PARAMETER ModName
  One mod folder name under the source root (e.g. versiontestMod). Omit with -All to link every mod.
.PARAMETER All
  Link every mod under the source root (any subfolder containing .metadata\metadata.json).
.PARAMETER Root
  Source worktree folder holding the mods (default: the mod1 master baseline). Junctions are
  created/cleared ONLY for mods present in THIS folder (user rule 2026-07-10) - running against a
  dev worktree never touches another worktree's junctions.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\link-mod-to-launcher.ps1 -ModName versiontestMod
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\link-mod-to-launcher.ps1 -All
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\link-mod-to-launcher.ps1 -All -Root ..\..\mod1-abc
#>
[CmdletBinding()]
param(
    [string]$ModName,
    [switch]$All,
    [string]$Root
)

$ErrorActionPreference = 'Stop'
if (-not $Root) { $Root = Join-Path $PSScriptRoot '..\..\mod1' }
$repoMods = Resolve-Path $Root | Select-Object -ExpandProperty Path
$docs     = [Environment]::GetFolderPath('MyDocuments')          # resolves the OneDrive redirect
$gameMod  = Join-Path $docs 'Paradox Interactive\Victoria 3\mod'

if (-not (Test-Path $gameMod)) { New-Item -ItemType Directory -Force $gameMod | Out-Null }

# build the work list
$names = @()
if ($All) {
    $names = Get-ChildItem $repoMods -Directory |
             Where-Object { Test-Path (Join-Path $_.FullName '.metadata\metadata.json') } |
             Select-Object -ExpandProperty Name
} elseif ($ModName) {
    $names = @($ModName)
} else {
    Write-Error "Specify -ModName <name> or -All."; exit 1
}

foreach ($name in $names) {
    $target = Join-Path $repoMods $name
    $link   = Join-Path $gameMod  $name

    if (-not (Test-Path (Join-Path $target '.metadata\metadata.json'))) {
        Write-Warning "[$name] no .metadata\metadata.json under mod1\ - skipping."
        continue
    }

    $existing = Get-Item $link -Force -ErrorAction SilentlyContinue
    if ($existing) {
        if ($existing.LinkType -eq 'Junction' -and ($existing.Target -contains $target)) {
            Write-Host "[$name] already junctioned correctly - OK."
            continue
        }
        # stale/dangling link or empty folder: remove it (refuse if it's a non-empty real dir).
        # A junction is removed regardless of where it points (dangling OR pointing at another
        # worktree) - scoping is by mod NAME in the source root, per the user rule 2026-07-10.
        $isJunction = $existing.Attributes.ToString() -match 'ReparsePoint'
        $hasChildren = @(Get-ChildItem $link -Force -ErrorAction SilentlyContinue).Count -gt 0
        if (-not $isJunction -and $hasChildren) {
            Write-Warning "[$name] a NON-EMPTY real folder exists at the link path - refusing to delete. Resolve manually."
            continue
        }
        # Robust, non-fatal removal: PS5.1 + EAP=Stop turns a native rmdir stderr into a
        # terminating error that used to kill the whole -All run - keep every attempt in
        # try/catch and fall through to the next method.
        try { attrib -R $link } catch {}
        try { [System.IO.Directory]::Delete($link) } catch {
            try { cmd /c "rmdir /q `"$link`"" } catch {}
        }
        if (Test-Path $link) { Write-Warning "[$name] could not remove stale entry (locked - OneDrive/session hold?) - skipping, re-run later."; continue }
    }

    New-Item -ItemType Junction -Path $link -Target $target | Out-Null
    $chk = Get-Item $link -Force
    if ($chk.LinkType -eq 'Junction' -and ($chk.Target -contains $target)) {
        Write-Host "[$name] junction created -> $target"
    } else {
        Write-Warning "[$name] created but does not verify as a junction (OneDrive may have materialised it). Re-run."
    }
}
