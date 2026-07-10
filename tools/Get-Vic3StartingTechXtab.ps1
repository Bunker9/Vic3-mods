param(
    [string]$Dir = "D:\Steam\steamapps\common\Victoria 3\game\common\history\countries",
    [string]$OutCsv = ".\vic3_starting_tech_xtab.csv"
)

$tierTechs = @{
    1 = @(
        'railways','intensive_agriculture','mechanical_tools','atmospheric_engine',
        'screw_frigate','general_staff','percussion_cap','power_of_the_purse',
        'dialectics','central_archives','central_banking','egalitarianism','corporate_charters'
    )
    2 = @(
        'mechanical_tools','atmospheric_engine',
        'dialectics','egalitarianism','corporate_charters'
    )
    3 = @(
        'enclosure','manufacturies','shaft_mining','distillation','steelworking','prospecting','cotton_gin',
        'military_drill','standing_army','navigation','gunsmithing','admiralty','artillery','drydocks',
        'mandatory_service','army_reserves','line_infantry',
        'urbanization','rationalism','tech_bureaucracy','democracy','romanticism','academia',
        'international_trade','international_relations','centralization','currency_standards',
        'colonization','urban_planning','law_enforcement','medical_degrees'
    )
    4 = @(
        'enclosure','manufacturies','steelworking','shaft_mining','distillation','prospecting',
        'military_drill','standing_army','navigation','admiralty','gunsmithing','artillery','drydocks',
        'urbanization','rationalism','tech_bureaucracy','centralization','democracy',
        'international_relations','international_trade'
    )
    5 = @(
        'enclosure','manufacturies','shaft_mining','international_trade',
        'standing_army','military_drill','navigation',
        'urbanization','rationalism','tech_bureaucracy'
    )
    6 = @(
        'enclosure','standing_army','urbanization'
    )
    7 = @()
}

$countries = @{}

function Merge-CountryBlock {
    param(
        [string]$Tag,
        [Nullable[int]]$Tier,
        [System.Collections.Generic.HashSet[string]]$ExplicitTechs
    )

    if ([string]::IsNullOrWhiteSpace($Tag)) { return }

    if (-not $countries.ContainsKey($Tag)) {
        $countries[$Tag] = [ordered]@{
            Tag = $Tag
            Tier = $null
            ExplicitTechs = [System.Collections.Generic.HashSet[string]]::new()
        }
    }

    if ($null -ne $Tier) {
        $countries[$Tag].Tier = $Tier
    }

    foreach ($tech in $ExplicitTechs) {
        [void]$countries[$Tag].ExplicitTechs.Add($tech)
    }
}

Get-ChildItem -Path $Dir -Recurse -File -Filter *.txt | ForEach-Object {
    $file = $_.FullName
    $lines = Get-Content -Path $file

    $inBlock = $false
    $depth = 0
    $tag = $null
    $tier = $null
    $explicitTechs = [System.Collections.Generic.HashSet[string]]::new()

    foreach ($line in $lines) {
        if (-not $inBlock) {
            if ($line -match '^\s*c:([A-Z0-9_]+)\s*\?=\s*\{') {
                $inBlock = $true
                $tag = $matches[1]
                $tier = $null
                $explicitTechs = [System.Collections.Generic.HashSet[string]]::new()

                if ($line -match 'effect_starting_technology_tier_([1-7])_tech\s*=\s*yes') {
                    $tier = [int]$matches[1]
                }

                foreach ($m in [regex]::Matches($line, 'add_technology_researched\s*=\s*([a-z0-9_]+)')) {
                    [void]$explicitTechs.Add($m.Groups[1].Value)
                }

                $depth = ([regex]::Matches($line, '\{')).Count - ([regex]::Matches($line, '\}')).Count
                if ($depth -le 0) {
                    Merge-CountryBlock -Tag $tag -Tier $tier -ExplicitTechs $explicitTechs
                    $inBlock = $false
                    $depth = 0
                    $tag = $null
                    $tier = $null
                    $explicitTechs = [System.Collections.Generic.HashSet[string]]::new()
                }
            }
        }
        else {
            if ($line -match 'effect_starting_technology_tier_([1-7])_tech\s*=\s*yes') {
                $tier = [int]$matches[1]
            }

            foreach ($m in [regex]::Matches($line, 'add_technology_researched\s*=\s*([a-z0-9_]+)')) {
                [void]$explicitTechs.Add($m.Groups[1].Value)
            }

            $depth += ([regex]::Matches($line, '\{')).Count
            $depth -= ([regex]::Matches($line, '\}')).Count

            if ($depth -le 0) {
                Merge-CountryBlock -Tag $tag -Tier $tier -ExplicitTechs $explicitTechs
                $inBlock = $false
                $depth = 0
                $tag = $null
                $tier = $null
                $explicitTechs = [System.Collections.Generic.HashSet[string]]::new()
            }
        }
    }

    if ($inBlock) {
        Merge-CountryBlock -Tag $tag -Tier $tier -ExplicitTechs $explicitTechs
    }
}

$expanded = @()
$allTechSet = [System.Collections.Generic.HashSet[string]]::new()

foreach ($entry in ($countries.GetEnumerator() | Sort-Object Key)) {
    $tag = $entry.Key
    $tier = $entry.Value.Tier
    $techSet = [System.Collections.Generic.HashSet[string]]::new()

    if ($null -ne $tier -and $tierTechs.ContainsKey([int]$tier)) {
        foreach ($tech in $tierTechs[[int]$tier]) {
            [void]$techSet.Add($tech)
            [void]$allTechSet.Add($tech)
        }
    }

    foreach ($tech in $entry.Value.ExplicitTechs) {
        [void]$techSet.Add($tech)
        [void]$allTechSet.Add($tech)
    }

    $expanded += [pscustomobject]@{
        Tag   = $tag
        Tier  = if ($null -ne $tier) { $tier } else { '-' }
        Techs = @($techSet | Sort-Object)
    }
}

$allTechs = @($allTechSet | Sort-Object)

$xtab = foreach ($country in $expanded) {
    $row = [ordered]@{
        Tag  = $country.Tag
        Tier = $country.Tier
    }

    $countryTechLookup = @{}
    foreach ($tech in $country.Techs) {
        $countryTechLookup[$tech] = $true
    }

    foreach ($tech in $allTechs) {
        $row[$tech] = if ($countryTechLookup.ContainsKey($tech)) { 1 } else { 0 }
    }

    [pscustomobject]$row
}

$xtab | Export-Csv -Path $OutCsv -NoTypeInformation -Encoding UTF8
$xtab | Format-Table -AutoSize

Write-Host ""
Write-Host "CSV written to: $OutCsv"
