<#
.SYNOPSIS
  READ-ONLY baseline audit for this machine: (Table 1) dual git-identity + credential isolation,
  (Table 2) age/vault health. Prints PASS/WARN/FAIL; never modifies anything.

.DESCRIPTION
  Design being verified:
    - DEFAULT account (XplanMagic, e.g. pmynguyen25) is gh's ACTIVE account + owns the GCM bare
      credential git:https://github.com. Authenticates via GCM ('manager').
    - VIC3 account (HershGord) is a --local override in mod1, authenticated via the gh helper
      ('!gh auth git-credential'). It is resolved by the username PINNED IN THE REMOTE URL
      (https://HershGord@github.com/...), so gh's default can stay the DEFAULT account.

  *** NEVER modifies git/credentials. *** It reads config, cmdkey, gh, and the age vault, then
  prints suggested fixes for YOU to run by hand. Expected values come from
  hk-config/config/gitidentity.json (gitignored). Structural fallback if that file is absent.

.PARAMETER ShowFixes
  Always print the suggested-fix block, even when everything passes.

.OUTPUTS
  Exit code = number of FAIL checks (0 = all good). WARNs do not affect the exit code.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File hk-config\scripts\githk_baseline_audit.ps1
#>
[CmdletBinding()]
param([switch]$ShowFixes)

# --- self-locating paths (no hardcoded username) ----------------------------
$scripts   = $PSScriptRoot
$hk        = Split-Path $scripts -Parent
$container = Split-Path $hk -Parent
$mod1      = Join-Path $container 'mod1'
$cfgPath   = Join-Path $hk 'config\gitidentity.json'
$bin       = Join-Path $hk 'bin'
$keyPath   = Join-Path $env:USERPROFILE '.vic3-vault\identity.key'

# --- reporting helpers ------------------------------------------------------
$script:fails = 0; $script:warns = 0; $script:fixes = @()
function Say([string]$s, [string]$m) {
  switch ($s) {
    'PASS' { Write-Host "  [PASS] $m" -ForegroundColor Green }
    'WARN' { Write-Host "  [WARN] $m" -ForegroundColor Yellow; $script:warns++ }
    'FAIL' { Write-Host "  [FAIL] $m" -ForegroundColor Red;    $script:fails++ }
    'INFO' { Write-Host "  [INFO] $m" -ForegroundColor Gray }
    default { Write-Host "  $m" }
  }
}
function Section([string]$t) { Write-Host ""; Write-Host "=== $t ===" -ForegroundColor Cyan }
function AddFix([string]$f) { $script:fixes += $f }

function GitVal { param([string]$Scope,[string]$Key,[string]$Repo)
  if ($Repo) { $v = & git -C $Repo config $Scope $Key } else { $v = & git config $Scope $Key }
  if ($null -eq $v) { return "" }
  return (($v | Out-String).Trim())
}

function Get-StoredCreds {
  $raw = cmdkey /list; $entries = @(); $curT = $null; $curU = $null
  foreach ($line in $raw) {
    if ($line -match 'Target:\s*(.+?)\s*$') {
      if ($curT) { $entries += [pscustomobject]@{ Target = $curT; User = $curU } }
      $curT = $matches[1].Trim(); $curU = $null
    } elseif ($line -match 'User:\s*(.+?)\s*$') { $curU = $matches[1].Trim() }
  }
  if ($curT) { $entries += [pscustomobject]@{ Target = $curT; User = $curU } }
  return $entries
}

function Get-GhAuth {
  $r = [pscustomobject]@{ Available = $false; Accounts = @(); Active = $null }
  try {
    $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $raw = & gh auth status 2>&1 | ForEach-Object { $_.ToString() }
    $ErrorActionPreference = $old
  } catch { return $r }
  if (-not $raw) { return $r }
  $r.Available = $true; $cur = $null
  foreach ($l in $raw) {
    if ($l -match 'account\s+(\S+)') { $cur = $matches[1]; $r.Accounts += $cur }
    if ($l -match 'Active account:\s*true' -and $cur) { $r.Active = $cur }
  }
  $r.Accounts = @($r.Accounts | Select-Object -Unique)
  return $r
}

# ============================================================================
Write-Host "############################################################" -ForegroundColor White
Write-Host "#  baseline audit  (READ-ONLY - modifies nothing)          #" -ForegroundColor White
Write-Host "############################################################" -ForegroundColor White

$cfg = $null
if (Test-Path $cfgPath) {
  try { $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json }
  catch { Say 'WARN' "gitidentity.json unreadable: $($_.Exception.Message)" }
}
$vic3Name  = if ($cfg) { $cfg.vic3_local.name } else { 'HershGord' }
if (-not $vic3Name) { $vic3Name = 'HershGord' }
$pinUser   = if ($cfg -and $cfg.vic3_local.remote_pin_user) { $cfg.vic3_local.remote_pin_user } else { $vic3Name }
$defActive = if ($cfg -and $cfg.gh.active_account) { $cfg.gh.active_account } else { $null }
if ($cfg) { Write-Host "  (baseline from config\gitidentity.json)" -ForegroundColor Gray }
else      { Write-Host "  (no gitidentity.json - structural checks only)" -ForegroundColor Gray }

# ====================== TABLE 1: GIT IDENTITY & ISOLATION ===================
Write-Host ""; Write-Host "################  TABLE 1 - git identity & credential isolation  ################" -ForegroundColor Magenta

Section "1. Global identity (system-wide default, NOT the Vic3 account)"
$gName = GitVal '--global' 'user.name'; $gEmail = GitVal '--global' 'user.email'
Say 'INFO' "global user.name = '$gName'"
if ($gName -eq $vic3Name) { Say 'FAIL' "global identity is the Vic3 account ($vic3Name) - leaked to global"; AddFix "Reset global to the default account: git config --global user.name/email <default>" }
elseif (-not $gName) { Say 'WARN' "global user.name empty" }
elseif ($cfg -and $gName -eq $cfg.default.name) { Say 'PASS' "global = default account ($($cfg.default.name))" }
else { Say 'PASS' "global is set and is NOT the Vic3 account ($gName)" }

Section "2. System identity (should be empty)"
$sName = GitVal '--system' 'user.name'
if (-not $sName) { Say 'PASS' "system user.name empty" } else { Say 'WARN' "system user.name = '$sName' (unexpected)" }

Section "3. Vic3 local identity (mod1 override = $vic3Name)"
if (Test-Path (Join-Path $mod1 '.git')) {
  $lName = GitVal '--local' 'user.name' $mod1
  Say 'INFO' "mod1 local user.name = '$lName'"
  if ($lName -eq $vic3Name) { Say 'PASS' "Vic3 local = $vic3Name" } else { Say 'FAIL' "Vic3 local '$lName' != $vic3Name"; AddFix "git -C `"$mod1`" config --local user.name $vic3Name" }
} else { Say 'WARN' "mod1\.git not found at $mod1" }

Section "4. Credential helper + GitHub auth mode (Vic3 uses GCM + PAT)"
$helperDump = & git config --show-origin --get-all credential.helper | Out-String
if ($helperDump -match 'manager') { Say 'PASS' "GCM ('manager') present (used by default account AND Vic3)" } else { Say 'WARN' "GCM ('manager') not in helper chain" }
if (Test-Path (Join-Path $mod1 '.git')) {
  $effHelper = GitVal '--get' 'credential.helper' $mod1   # effective (winning) value
  if ($effHelper -match 'manager') { Say 'PASS' "Vic3 effective helper = GCM (manager)" } else { Say 'WARN' "Vic3 effective helper = '$effHelper' (expected manager)" }
  $authModes = GitVal '--local' 'credential.gitHubAuthModes' $mod1
  $expModes  = if ($cfg -and $cfg.vic3_local.github_auth_modes) { $cfg.vic3_local.github_auth_modes } else { 'pat' }
  if ($authModes -eq $expModes) { Say 'PASS' "Vic3 credential.gitHubAuthModes = $authModes (repo-scoped -> PAT prompt only here, never Karen)" }
  else { Say 'WARN' "Vic3 gitHubAuthModes = '$authModes' (expected '$expModes')"; AddFix "git -C `"$mod1`" config --local credential.gitHubAuthModes $expModes" }
}

Section "5. Remote URL pinned to the Vic3 account ($pinUser@)"
if (Test-Path (Join-Path $mod1 '.git')) {
  $url = (& git -C $mod1 remote get-url origin 2>$null)
  if ($null -ne $url) { $url = $url.Trim() }
  Say 'INFO' "origin = $url"
  if ($url -match "^https://$pinUser@github\.com/") { Say 'PASS' "origin pins $pinUser@ -> gh resolves the Vic3 token while default stays active" }
  elseif ($url -match "^https://github\.com/") { Say 'FAIL' "origin is BARE (no $pinUser@) -> gh serves the ACTIVE (default) account -> Vic3 push uses the wrong identity"; AddFix "git remote set-url origin $($cfg.vic3_local.remote_url)" }
  elseif ($url -match "@github\.com/") { Say 'WARN' "origin pins a different user than $pinUser ($url)" }
  else { Say 'WARN' "origin not an https github URL ($url)" }
}

Section "6. Windows credential store (bare host key - INFORMATIONAL under the gh-active-account design)"
# Current design: the DEFAULT account authenticates github.com via the gh CLI helper bound to gh's
# ACTIVE account (Section 7), NOT via the bare git:https://github.com GCM cred. Vic3 authenticates as
# $vic3Name via the URL-pinned key git:https://$pinUser@github.com (local 'manager' helper + the
# $pinUser@ remote). So the OWNER of the bare key no longer gates anyone's auth -> it is informational,
# not a failure (it is harmless leftover from a past 'gh auth setup-git'). The real Vic3 invariant is
# that the ISOLATED key exists and caches the Vic3 PAT.
$creds = Get-StoredCreds
$bare  = $creds | Where-Object { $_.Target -match 'target=git:https://github\.com$' } | Select-Object -First 1
$iso   = $creds | Where-Object { $_.Target -match "target=git:https://$pinUser@github\.com$" } | Select-Object -First 1
if ($bare) { Say 'INFO' "bare 'git:https://github.com' owned by: $($bare.User) (does not gate auth under the current design)" }
else       { Say 'INFO' "no bare 'git:https://github.com' cred (fine - the gh helper serves the active account)" }
if ($iso)  { Say 'PASS' "Vic3 token isolated under git:https://$pinUser@github.com ($($iso.User))" }
else       { Say 'WARN' "no isolated 'git:https://$pinUser@github.com' cred cached yet - run one real Vic3 push to store the $vic3Name PAT" }

Section "7. gh CLI (the DEFAULT account's github.com auth path - active account must NOT be Vic3)"
# The global credential.https://github.com.helper is the gh helper, which serves gh's ACTIVE account.
# So the default account's github.com pushes auth as whoever gh has active -> that must be the default,
# never the Vic3 account. Vic3 itself is isolated by its repo-local 'manager' helper + $pinUser@ URL,
# so it is unaffected by gh's active account.
$gh = Get-GhAuth
if (-not $gh.Available) { Say 'WARN' "gh unavailable / not logged in - the default account authenticates github.com via the gh helper, so gh should be logged in as it" }
else {
  Say 'INFO' "gh accounts: $($gh.Accounts -join ', '); active: $($gh.Active)"
  $expActive = if ($cfg -and $cfg.gh.active_account) { $cfg.gh.active_account } else { $defActive }
  if ($expActive -and $gh.Active -eq $vic3Name) { Say 'FAIL' "gh active account is the Vic3 account ($vic3Name) -> the default account's pushes would auth as Vic3"; AddFix "gh auth switch --user $expActive" }
  elseif ($expActive -and $gh.Active -eq $expActive) { Say 'PASS' "gh active = default ($($gh.Active)) -> resolves the default account's github.com auth; Vic3 is isolated by URL pin" }
  elseif ($expActive) { Say 'WARN' "gh active = '$($gh.Active)' (expected default '$expActive')" }
  else { Say 'INFO' "no expected gh.active_account in gitidentity.json (cannot assert active account)" }
}

Section "8. Write-auth test (push --dry-run; the REAL test - ls-remote is anonymous on a public repo)"
if (Test-Path (Join-Path $mod1 '.git')) {
  $env:GIT_TERMINAL_PROMPT = '0'
  & git -C $mod1 push --dry-run 2>&1 | Out-Null
  if ($LASTEXITCODE -eq 0) { Say 'PASS' "push --dry-run OK -> HershGord PAT authenticates for write" }
  else { Say 'WARN' "push --dry-run failed (exit $LASTEXITCODE) - PAT not cached/valid; run one real 'git push' to store it" }
}

# ====================== TABLE 2: AGE / VAULT HEALTH =========================
Write-Host ""; Write-Host "################  TABLE 2 - age / vault health  ################" -ForegroundColor Magenta

Section "A. Binaries & keys present"
$ageExe = Join-Path $bin 'age.exe'; $ageKg = Join-Path $bin 'age-keygen.exe'; $vaultPub = Join-Path $bin 'vault.pub'
if (Test-Path $ageExe)   { Say 'PASS' "age.exe present" }          else { Say 'FAIL' "age.exe missing in bin/" }
if (Test-Path $ageKg)    { Say 'PASS' "age-keygen.exe present" }   else { Say 'WARN' "age-keygen.exe missing in bin/" }
if (Test-Path $vaultPub) { Say 'PASS' "vault.pub present" }        else { Say 'FAIL' "vault.pub missing in bin/" }
if (Test-Path $keyPath)  { Say 'PASS' "private key present (~/.vic3-vault/identity.key)" } else { Say 'FAIL' "private key NOT found at $keyPath"; AddFix "restore identity.key from DR (email subject token), then: python bin/hkvault.py unseal" }

Section "B. Keypair match (derived pub == vault.pub)"
if ((Test-Path $ageKg) -and (Test-Path $keyPath) -and (Test-Path $vaultPub)) {
  try {
    $derived = (& $ageKg -y $keyPath 2>$null | Out-String).Trim()
    $stored  = (Get-Content $vaultPub -Raw).Trim()
    if ($derived -and $derived -eq $stored) { Say 'PASS' "keypair MATCH (private key decrypts the vault)" }
    else { Say 'FAIL' "keypair MISMATCH - the private key does NOT match vault.pub" }
  } catch { Say 'WARN' "could not derive pubkey: $($_.Exception.Message)" }
} else { Say 'WARN' "skipped keypair check (missing key/keygen/pub)" }

Section "C. git aliases (seal / unseal / vault)"
$aliasDump = (& git -C $hk config --get-regexp '^alias\.(seal|unseal|vault)$' 2>$null | Out-String)
$have = @('seal','unseal','vault') | Where-Object { $aliasDump -match "alias\.$_\b" }
if ($have.Count -eq 3) { Say 'PASS' "all three vault aliases configured" }
elseif ($have.Count -gt 0) { Say 'WARN' "only these vault aliases set: $($have -join ', ')  (run bin/install.bat)" }
else { Say 'WARN' "vault aliases not configured (run bin/install.bat)" }

Section "D. git vault verify (no plaintext .md tracked; decrypt-test)"
try {
  $vaultOut = (& git -C $hk vault 2>&1 | Out-String)
  if ($LASTEXITCODE -eq 0) { Say 'PASS' "git vault verify passed (0 plaintext .md tracked, decrypt-test clean)" }
  else { Say 'FAIL' "git vault verify FAILED: $($vaultOut.Trim())" }
} catch { Say 'WARN' "could not run git vault: $($_.Exception.Message)" }

# ============================ SUMMARY =======================================
Section "SUMMARY"
$verdict = if ($script:fails -gt 0) { 'FAIL' } elseif ($script:warns -gt 0) { 'WARN' } else { 'ALL PASS' }
$color   = if ($script:fails -gt 0) { 'Red' } elseif ($script:warns -gt 0) { 'Yellow' } else { 'Green' }
Write-Host "  $($script:fails) failure(s), $($script:warns) warning(s)  ->  $verdict" -ForegroundColor $color

if (($script:fixes.Count -gt 0) -or $ShowFixes) {
  Section "SUGGESTED FIXES (run these YOURSELF - this script will not)"
  if ($script:fixes.Count -eq 0) { Write-Host "  (nothing to fix)" -ForegroundColor Gray }
  $i = 1; foreach ($f in $script:fixes) { Write-Host "  $i) $f" -ForegroundColor Yellow; $i++ }
  Write-Host ""
  Write-Host "  Reminder: git/credential restoration is done BY HAND, not by Claude." -ForegroundColor Gray
}
exit $script:fails
