<#
.SYNOPSIS
  Roll all three Vic3-mods worktrees back to a CHECKPOINT (see tools\checkpoint.ps1),
  so you can inspect a known-good state across code + testbook + hk/config at once.

  Each worktree is left at DETACHED HEAD on its leg tag. Your branches are untouched;
  to return, run  git checkout <branch>  in each worktree (printed at the end).

.EXAMPLE
  pwsh tools\checkpoint-restore.ps1 -Name matcha-2026-06-11
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)][string]$Name,   # checkpoint id, e.g. matcha-2026-06-11
  [switch]$Force,                         # restore even if a worktree has uncommitted changes
  # self-locating: this script lives in <container>\hk-config\tools\
  [string]$RepoRoot = (Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "mod1")
)
$ErrorActionPreference = "Stop"

$legs = @(
  @{ name='code';     tag="$Name/code";     branch='test/versiontest' },
  @{ name='testbook'; tag="$Name/testbook"; branch='testbook' },
  @{ name='hkconfig'; tag="$Name/hkconfig"; branch='hk/config' }
)

# discover worktree path per branch
$wt = @{}; $cur = $null
foreach ($line in (& git -C $RepoRoot worktree list --porcelain)) {
  if     ($line -like 'worktree *') { $cur = $line.Substring(9) }
  elseif ($line -like 'branch *')   { $wt[($line.Substring(7) -replace '^refs/heads/','')] = $cur }
}

# pre-flight: tags exist + trees clean (fail before changing anything)
foreach ($leg in $legs) {
  & git -C $RepoRoot rev-parse -q --verify "refs/tags/$($leg.tag)" *> $null
  if ($LASTEXITCODE -ne 0) { throw "missing tag $($leg.tag) - is checkpoint '$Name' complete?" }
  $path = $wt[$leg.branch]
  if (-not $path) { throw "no worktree on branch '$($leg.branch)' for leg $($leg.name)" }
  $leg.path = $path
  if (-not $Force) {
    $dirty = & git -C $path status --porcelain
    if ($dirty) { throw "$($leg.name) worktree has uncommitted changes ($path). Commit/stash, or use -Force." }
  }
}

foreach ($leg in $legs) {
  & git -C $leg.path checkout --quiet $leg.tag
  if ($LASTEXITCODE -ne 0) { throw "checkout failed for $($leg.name)" }
  Write-Host ("{0,-9} -> {1}   ({2})" -f $leg.name, $leg.tag, $leg.path)
}

Write-Host ""
Write-Host "All three worktrees restored to checkpoint '$Name' (detached HEAD)."
Write-Host "To return to normal work, in each worktree run:"
foreach ($leg in $legs) { Write-Host ("  git -C `"{0}`" checkout {1}" -f $leg.path, $leg.branch) }
