param(
    [ValidateSet('ordmantell','korriban','boz','echo')][string]$Map = 'ordmantell',
    [string]$Name = ('converted-' + $Map + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
)
$ErrorActionPreference = 'Stop'
$Configurations = @{
    echo = @{ Audit='outputs/CONVERTED-PEB-088.json'; Manifest='work/world-echo088.txt'; Scale='0.9259259259259259'; Replay='work/coverage085-echo-replay.txt'; Stop=2480; Start=2479; HdStart=2465 }
    boz = @{ Audit='outputs/CONVERTED-BOZ-084.json'; Manifest='work/world-boz084.txt'; Scale='0.8333333333333333'; Replay='work/coverage084-boz-replay.txt'; Stop=2416; Start=2415; HdStart=2401 }
    ordmantell = @{ Audit='outputs/CONVERTED-PSO-083.json'; Manifest='work/world-ordmantell083.txt'; Scale='0.8333333333333333'; Replay='work/converted082-ordmantell-replay.txt'; Stop=2576; Start=2575; HdStart=2561 }
    korriban = @{ Audit='outputs/CONVERTED-KOR-083.json'; Manifest='work/world-korriban083.txt'; Scale='0.8888888888888889'; Replay='work/coverage083-korriban-replay.txt'; Stop=2512; Start=2511; HdStart=2497 }
}
Push-Location $PSScriptRoot
try {
    $Config = $Configurations[$Map]
    if ($Map -eq 'boz') { & python work/stage-boz084.py }
    elseif ($Map -eq 'echo') {
        $StagePython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
        if (!(Test-Path -LiteralPath $StagePython)) { throw 'The configured Python runtime for verified vertex staging is missing.' }
        & $StagePython work/stage-echo088.py
    }
    else { & python work/stage-world083.py $Config.Audit $Config.Manifest $Config.Scale }
    if ($LASTEXITCODE -ne 0) { throw 'Converted map source verification failed.' }
    $Manifest = Join-Path $PSScriptRoot $Config.Manifest
    $Report = Join-Path $PSScriptRoot "work/runs/$Name/world-report.jsonl"
    $RunArguments = @('work/project/tools/run010.py', $Name,
        '--exe','work/build-windows-native/bin/RenegadeNative.exe',
        '--root','work','--dll-dir','work/windows-sdk/bin','--isolate-executable',
        '--vblanks',[string]$Config.Stop,'--timeout','900','--start',[string]$Config.Start,'--stride','120',
        '--replay',$Config.Replay,
        '--env','PSPRECOMP_FRAME_LIMIT=0','--env','PSPRECOMP_RASTER_THREADS=1',
        '--env','PSPRECOMP_GE_BACKEND=software',
        '--env','RENEGADE_HD_CAPTURE=1','--env',"RENEGADE_HD_START_VBLANK=$($Config.HdStart)",
        '--env','RENEGADE_FXAA=1','--env',"RENEGADE_WORLD_GEOMETRY=$Manifest",
        '--env',"RENEGADE_WORLD_REPORT=$Report",'--env','RENEGADE_TRACE_MODEL_DRAWS=1',
        '--env',('RENEGADE_OVERRIDE_ROOT=' + (Join-Path $PSScriptRoot 'work/mods-textures-source074')))
    & python @RunArguments
    if ($LASTEXITCODE -ne 0) { throw "Converted map capture failed: $LASTEXITCODE" }
    Write-Host "1280x720 FXAA capture: work/runs/$Name/frames/render-720p-fxaa"
    Write-Host "Verified world replacement counts: work/runs/$Name/world-report.jsonl"
} finally { Pop-Location }
