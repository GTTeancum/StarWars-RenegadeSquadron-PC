param(
    [string]$Name = ('textures-' + (Get-Date -Format 'yyyyMMdd-HHmmss')),
    [switch]$OriginalBaseline,
    [string]$OverridePack = 'work/mods-textures-source074'
)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $RunArguments = @('work/project/tools/run010.py', $Name,
        '--exe','work/build-windows-native/bin/RenegadeNative.exe',
        '--root','work','--dll-dir','work/windows-sdk/bin','--isolate-executable',
        '--vblanks','2640','--timeout','480','--start','2519','--stride','120',
        '--replay','work/source060-echo-replay.txt',
        '--env','PSPRECOMP_FRAME_LIMIT=0','--env','PSPRECOMP_RASTER_THREADS=1',
        '--env','PSPRECOMP_GE_BACKEND=software',
        '--env','RENEGADE_HD_CAPTURE=1',
        '--env','RENEGADE_FXAA=1',
        '--env','RENEGADE_HD_START_VBLANK=2505')
    if (!$OriginalBaseline) {
        $Pack = if ([IO.Path]::IsPathRooted($OverridePack)) { $OverridePack } else { Join-Path $PSScriptRoot $OverridePack }
        if (!(Test-Path -LiteralPath $Pack)) { throw "Missing supplied-texture pack: $Pack" }
        $RunArguments += @('--env',"RENEGADE_OVERRIDE_ROOT=$Pack")
    }
    & python @RunArguments
    if ($LASTEXITCODE -ne 0) { throw "Headless capture failed with exit $LASTEXITCODE" }
    Write-Host "720p FXAA captures: work/runs/$Name/frames/render-720p-fxaa"
    Write-Host "Unfiltered captures: work/runs/$Name/frames/render-720p"
    Write-Host 'Diagnostic 1280x720 shadow render; original guest VRAM captures are retained alongside it.'
} finally { Pop-Location }
