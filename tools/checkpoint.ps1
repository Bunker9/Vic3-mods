<#
.SYNOPSIS
  Stamp a CHECKPOINT across the three Vic3-mods worktrees so a tested state can be
  correlated and rolled back together: code (validated mods) + testbook (the test
  artifacts that validated it) + hk/config (the design/data behind it).

  These three branches have UNRELATED histories, so one tag name can't span them.
  A checkpoint is therefore three annotated tags sharing a prefix:
        <name>/code   <name>/testbook   <name>/hkconfig
  Each tag's message records the other two SHAs (the correlation glue).

.EXAMPLE
  pwsh tools\checkpoint.ps1 -GameVersion 1.13.8 -Note "3 mods green; Sindh annex + eco census" -Push
  # -> tags  matcha-2026-06-11/{code,testbook,hkconfig}

.NOTES
  Codename = the Vic3 minor line you're chasing (1.13.x = "Matcha"). Bump it when the
  game's codename changes (1.14 -> new name). This is NOT a public "release"; it's a
  private troubleshooting anchor. Restore with tools\checkpoint-restore.ps1.
#>
[CmdletBinding()]
param(
  [string]$Codename       = "matcha",
  [string]$GameVersion    = "",                 # exact Vic3 build validated, e.g. 1.13.8
  [string]$Note           = "",                 # one-line description of this state
  [string]$Name           = "",                 # override full checkpoint id (default <codename>-<date>)
  [string]$CodeBranch     = "test/versiontest", # the validated "code" leg
  [string]$TestbookBranch = "testbook",
  [string]$HkBranch       = "hk/config",
  [switch]$Push,                                # also push the 3 tags to origin
  # self-locating: this script lives in <container>\hk-config\tools\
  [string]$RepoRoot = (Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "mod1"),
  [string]$LogFile  = (Join-Path (Split-Path $PSScriptRoot -Parent) "CHECKPOINTS.md")
)
$ErrorActionPreference = "Stop"
function Git { & git -C $RepoRoot @args; if ($LASTEXITCODE -ne 0) { throw "git failed: $args" } }

if (-not $Name) { $Name = "$Codename-$(Get-Date -Format 'yyyy-MM-dd')" }
if (-not $GameVersion) { Write-Warning "No -GameVersion given - record which Vic3 build this was validated against for traceability." }

# refuse to overwrite an existing checkpoint of the same name
foreach ($leg in 'code','testbook','hkconfig') {
  & git -C $RepoRoot rev-parse -q --verify "refs/tags/$Name/$leg" *> $null
  if ($LASTEXITCODE -eq 0) { throw "checkpoint '$Name' already has tag $Name/$leg - choose a new -Name." }
}

$code = (Git rev-parse --short $CodeBranch).Trim()
$tb   = (Git rev-parse --short $TestbookBranch).Trim()
$hk   = (Git rev-parse --short $HkBranch).Trim()

$body = @"
Checkpoint: $Name
Vic3: $GameVersion
Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm')
Note: $Note
Legs (roll all three together to reproduce this state):
  code     = $code  ($CodeBranch)
  testbook = $tb  ($TestbookBranch)
  hkconfig = $hk  ($HkBranch)
"@

Git tag -a "$Name/code"     $CodeBranch     -m $body
Git tag -a "$Name/testbook" $TestbookBranch -m $body
Git tag -a "$Name/hkconfig" $HkBranch       -m $body
Write-Host "Created checkpoint tags:  $Name/{code,testbook,hkconfig}"
Write-Host "  code     $code  ($CodeBranch)"
Write-Host "  testbook $tb  ($TestbookBranch)"
Write-Host "  hkconfig $hk  ($HkBranch)"

if ($Push) {
  Git push origin "refs/tags/$Name/code" "refs/tags/$Name/testbook" "refs/tags/$Name/hkconfig"
  Write-Host "Pushed 3 tags to origin."
}

if (-not (Test-Path $LogFile)) {
  Set-Content -Path $LogFile -Encoding utf8 -Value "# Vic3-mods checkpoints`r`n`r`n(private index; reconstructable from ``git tag -n``)`r`n"
}
Add-Content -Path $LogFile -Encoding utf8 -Value ("- **{0}** - Vic3 {1} - code {2} / testbook {3} / hkconfig {4} - {5}" -f $Name,$GameVersion,$code,$tb,$hk,$Note)
Write-Host "Logged to $LogFile"
