param(
    [ValidatePattern('^[a-zA-Z0-9_-]+$')]
    [string]$Name = ('render-' + (Get-Date -Format 'yyyyMMdd-HHmmss')),
    [switch]$OriginalBaseline,
    [string]$OverridePack = 'work/mods-textures-source074',
    [ValidateSet('Software','DirectX12')]
    [string]$Renderer = 'Software',
    [switch]$ExperimentalHDComposition
)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $Report = Join-Path $PSScriptRoot "work/runs/$Name/render-report.jsonl"
    $Dump = Join-Path $PSScriptRoot 'work/texture-dumps-live/textures'
    New-Item -ItemType Directory -Path $Dump -Force | Out-Null
    $RunArguments = @('work/project/tools/run010.py', $Name,
        '--exe','work/build-windows-native/bin/RenegadeNative.exe',
        '--root','work','--dll-dir','work/windows-sdk/bin','--isolate-executable',
        '--vblanks','2480','--timeout','900','--start','2479','--stride','120',
        '--replay','work/coverage085-echo-replay.txt',
        '--env','PSPRECOMP_WINDOW=0','--env','SDL_VIDEODRIVER=dummy',
        '--env','PSPRECOMP_FRAME_LIMIT=0','--env','PSPRECOMP_RASTER_THREADS=1',
        '--env',"PSPRECOMP_GE_BACKEND=$(if ($Renderer -eq 'DirectX12') {'directx12'} else {'software'})",'--env','RENEGADE_OUTPUT_RESOLUTION=1280x720',
        '--env',"RENEGADE_HD_CAPTURE=$(if ($Renderer -eq 'DirectX12') {'0'} else {'1'})",'--env',"RENEGADE_HD_PRESENT=$(if ($Renderer -eq 'DirectX12') {'0'} else {'1'})",
        '--env','RENEGADE_FXAA=1','--env','RENEGADE_HD_START_VBLANK=2465',
        '--env',"RENEGADE_RENDER_REPORT=$Report",'--env','RENEGADE_RENDER_START_VBLANK=2465',
        '--env',"RENEGADE_DUMP_TEXTURES=$Dump",
        '--env',"RENEGADE_HD_SURFACE_TEXTURES=$(if ($ExperimentalHDComposition) {'1'} else {'0'})")
    if (!$OriginalBaseline) {
        $Pack = if ([IO.Path]::IsPathRooted($OverridePack)) { $OverridePack } else { Join-Path $PSScriptRoot $OverridePack }
        if (!(Test-Path -LiteralPath (Join-Path $Pack 'textures'))) { throw "Missing texture pack: $Pack" }
        if ($Renderer -eq 'DirectX12' -and (Test-Path -LiteralPath (Join-Path $Pack 'models'))) { throw 'GPU preview supports texture-only packs.' }
        $RunArguments += @('--env',"RENEGADE_OVERRIDE_ROOT=$Pack")
    }
    $Config = Join-Path $PSScriptRoot $(if ($Renderer -eq 'DirectX12') {'work/rendering/dx12-preview.ini'} else {'work/rendering/software.ini'})
    $RunArguments += @('--env',"PSPRECOMP_CONFIG=$Config")
    if ($Renderer -eq 'DirectX12') {
        $RunArguments += @('--env','PSPRECOMP_DX12_GE_STRICT=1','--env','PSPRECOMP_DX12_GE_READBACK=1',
            '--env','PSPRECOMP_GE_GPU_SKIP_SOFTWARE_RASTER=0','--env','PSPRECOMP_GE_GPU_HW_TRANSFORM=0','--env','PSPRECOMP_GE_GPU_HW_CULL=0',
            '--env','PSPRECOMP_GE_GPU_DUMP_VBLANK=2479','--env',"PSPRECOMP_GE_GPU_DUMP_PATH=$(Join-Path $PSScriptRoot "work/runs/$Name/gpu.ppm")")
    }
    & python @RunArguments
    if ($LASTEXITCODE -ne 0) { throw "Rendering capture failed with exit $LASTEXITCODE" }
    Write-Host "Render report: $Report"
    Write-Host "720p captures: $(if ($Renderer -eq 'DirectX12') {"work/runs/$Name/gpu.ppm and gpu-fxaa.ppm"} else {"work/runs/$Name/frames (unfiltered, HUD-preserving FXAA, whole-frame FXAA comparison)"})"
} finally { Pop-Location }
