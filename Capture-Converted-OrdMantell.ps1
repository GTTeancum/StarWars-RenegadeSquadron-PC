param([string]$Name = ('converted-ordmantell-' + (Get-Date -Format 'yyyyMMdd-HHmmss')))
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & python work/stage-world082.py
    if ($LASTEXITCODE -ne 0) { throw 'Converted map source verification failed.' }
    $Manifest = Join-Path $PSScriptRoot 'work/world-ordmantell082.txt'
    $RunArguments = @('work/project/tools/run010.py', $Name,
        '--exe','work/build-windows-native/bin/RenegadeNative.exe',
        '--root','work','--dll-dir','work/windows-sdk/bin','--isolate-executable',
        '--vblanks','2576','--timeout','900','--start','2575','--stride','120',
        '--replay','work/converted082-ordmantell-replay.txt',
        '--env','PSPRECOMP_FRAME_LIMIT=0','--env','PSPRECOMP_RASTER_THREADS=1',
        '--env','PSPRECOMP_GE_BACKEND=software',
        '--env','RENEGADE_HD_CAPTURE=1','--env','RENEGADE_HD_START_VBLANK=2561',
        '--env','RENEGADE_FXAA=1','--env',"RENEGADE_WORLD_GEOMETRY=$Manifest",
        '--env','RENEGADE_TRACE_MODEL_DRAWS=1',
        '--env',('RENEGADE_OVERRIDE_ROOT=' + (Join-Path $PSScriptRoot 'work/mods-textures-source074')))
    & python @RunArguments
    if ($LASTEXITCODE -ne 0) { throw "Converted map capture failed: $LASTEXITCODE" }
    Write-Host "1280x720 FXAA capture: work/runs/$Name/frames/render-720p-fxaa"
} finally { Pop-Location }
