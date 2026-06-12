<#
.SYNOPSIS
  Add a UTF-8 BOM to Vic3 script/loc files (.txt / .yml) that need one.
.DESCRIPTION
  Vic3 requires a UTF-8 BOM on common/**/*.txt and localization/**/*.yml; the editor/Write
  tooling often writes them WITHOUT a BOM, which the testbook static check flags. This is the
  reusable form of the inline one-liner used during authoring (see memory vic3-scripting-gotchas).
  Idempotent: files that already start with EF BB BF are skipped.
.PARAMETER Paths
  One or more file paths (absolute or relative to CWD). Accepts pipeline input.
.EXAMPLE
  ./envSetup_add_bom.ps1 mod1/InfraTaxMod/common/on_actions/infratax_on_actions.txt
.EXAMPLE
  Get-ChildItem mod1/InfraTaxMod -Recurse -Include *.txt,*.yml | ./envSetup_add_bom.ps1
#>
[CmdletBinding()]
param([Parameter(ValueFromPipeline = $true, ValueFromRemainingArguments = $true)][string[]]$Paths)
begin { $enc = New-Object System.Text.UTF8Encoding($true) }
process {
    foreach ($p in $Paths) {
        $full = (Resolve-Path $p).Path
        $bytes = [System.IO.File]::ReadAllBytes($full)
        if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
            Write-Host "skip (has BOM): $p"; continue
        }
        $text = Get-Content $full -Raw -Encoding UTF8
        [System.IO.File]::WriteAllText($full, $text, $enc)
        Write-Host "BOM added: $p"
    }
}
