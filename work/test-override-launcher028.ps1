param([string]$ResultPath)
$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot
$Launcher = Join-Path $Repo 'Play-RenegadeSquadronPC.ps1'
$Results = @()
$SpacePack = Join-Path $PSScriptRoot 'launcher028 pack'
New-Item -ItemType Directory -Force -Path (Join-Path $SpacePack 'models') | Out-Null
$env:RENEGADE_OVERRIDE_ROOT = 'deliberately-inherited-invalid-pack'
$env:RENEGADE_DUMP_TEXTURES = 'deliberately-inherited-dump'

function Check-Launch([string]$Name, [string[]]$Arguments, [bool]$Success, [string]$Expected) {
    $Lines = & powershell -NoProfile -ExecutionPolicy Bypass -File $Launcher @Arguments 2>&1
    $Code = $LASTEXITCODE
    $Text = $Lines | Out-String
    $Passed = (($Code -eq 0) -eq $Success) -and $Text.Contains($Expected)
    if ($Success) {
        $Passed = $Passed -and $Text.Contains('Controls:   modern') -and
            $Text.Contains('SDL_XINPUT_ENABLED=1') -and $Text.Contains('Dry run only')
        if ($Arguments -contains '-DiscoverAssets') {
            $Match = [regex]::Match($Text, '(?m)^  Discovery:  (.+)$')
            $Passed = $Passed -and $Match.Success -and !(Test-Path -LiteralPath $Match.Groups[1].Value.Trim())
        }
    }
    $script:Results += [pscustomobject]@{name=$Name;passed=$Passed;exit_code=$Code;output=$Text}
}

Check-Launch 'default ignores inherited pack' @('-DryRun') $true 'Off (original assets)'
Check-Launch 'relative valid pack' @('-DryRun','-OverridePack','work\mods-model027') $true (Join-Path $PSScriptRoot 'mods-model027')
Check-Launch 'absolute path with spaces' @('-DryRun','-OverridePack',$SpacePack) $true $SpacePack
Check-Launch 'opt-in discovery' @('-DryRun','-DiscoverAssets') $true 'Asset discovery is enabled'
Check-Launch 'missing path' @('-DryRun','-OverridePack','work\absent-launcher028-pack') $false 'Override pack folder not found'
Check-Launch 'wrong folder layout' @('-DryRun','-OverridePack','work\mods-model027\models') $false 'Override pack needs a models or textures folder'
Push-Location $env:TEMP
try { Check-Launch 'relative path independent of caller directory' @('-DryRun','-OverridePack','work\mods-model027') $true (Join-Path $PSScriptRoot 'mods-model027') }
finally { Pop-Location }
if (!$ResultPath) { $ResultPath = Join-Path $Repo ('outputs\LAUNCHER-' + (Get-Date -Format 'yyyyMMdd-HHmmss-ffff') + '-results.json') }
$Results | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $ResultPath
$Results | Select-Object name,passed,exit_code | Format-Table
if ($Results.passed -contains $false) { exit 1 }
exit 0
