param(
    [ValidateSet('modern','legacy')]
    [string]$Controls = 'modern',

    [ValidateSet('480x272','960x544','1440x816','1920x1088','1280x720','1920x1080')]
    [string]$Resolution = '1280x720',
    # PC: optimized build, graphics-card rendering presented straight to the window,
    # 60 fps game cap, per-pixel lighting, bloom and sun shadows (each can be turned off).
    [ValidateSet('PC','Software','DirectX12')]
    [string]$Renderer = 'PC',
    [double]$FrameRateCap = 60,
    [switch]$NoPerPixelLighting,
    [switch]$NoBloom,
    [switch]$NoShadows,
    [switch]$SmoothFog,

    [double]$LookX = 1.0,
    [double]$LookY = 1.0,
    [double]$LookCurve = 1.0,
    [double]$LeftDeadzone = 0.2394,
    [double]$RightDeadzone = 0.2652,
    [double]$TriggerThreshold = 0.1176,

    [switch]$InvertY,
    [switch]$DryRun,
    [switch]$NativeRendering,
    [switch]$NoFXAA,
    [switch]$NoTextureDump,
    [switch]$InspectTextures,
    [switch]$ExperimentalHDComposition,
    [string]$TextureDumpDirectory = 'work/texture-dumps-live/textures',

    # Relative pack paths resolve from the repository, regardless of caller cwd.
    [string]$OverridePack = $(@('work/mods-textures-source074','work/mods-textures-source072','work/mods-textures-source071','work/mods-textures-source069','work/mods-textures-source068','work/mods-textures-source067','work/mods-textures-source066','work/mods-textures-source065','work/mods-textures-source064','work/mods-textures-source063','work/mods-textures-source062','work/mods-textures-source061') | Where-Object { Test-Path -LiteralPath (Join-Path $PSScriptRoot $_) } | Select-Object -First 1),
    [switch]$DiscoverAssets,

    [UInt64]$DispatchBudget = 1000000000000
)

$ErrorActionPreference = 'Stop'
$RepoRoot = $PSScriptRoot
$WorkRoot = Join-Path $RepoRoot 'work'
$Exe = Join-Path $WorkRoot $(if ($Renderer -eq 'PC') { 'build-perf\bin\RenegadeNative.exe' } else { 'build-windows-native\bin\RenegadeNative.exe' })
$Boot = Join-Path $WorkRoot 'game\disc\PSP_GAME\SYSDIR\BOOT.BIN'
$Disc = Join-Path $WorkRoot 'game\disc'

$SelectedPack = $null
if (![string]::IsNullOrWhiteSpace($OverridePack)) {
    $PackPath = if ([IO.Path]::IsPathRooted($OverridePack)) { $OverridePack } else { Join-Path $RepoRoot $OverridePack }
    if (!(Test-Path -LiteralPath $PackPath -PathType Container)) { throw "Override pack folder not found: $PackPath" }
    $SelectedPack = (Resolve-Path -LiteralPath $PackPath).ProviderPath
    $HasModels = Test-Path -LiteralPath (Join-Path $SelectedPack 'models') -PathType Container
    $HasTextures = Test-Path -LiteralPath (Join-Path $SelectedPack 'textures') -PathType Container
    if (!$HasModels -and !$HasTextures) { throw "Override pack needs a models or textures folder: $SelectedPack" }
    if ($Renderer -ne 'Software' -and $HasModels) { throw 'GPU preview supports texture-only packs; use Software for MSH/model packs.' }
}
if ($Renderer -ne 'Software' -and $NativeRendering) { throw 'GPU preview renders at 1280x720; omit -NativeRendering or select Software.' }

$SdlDll = Get-ChildItem -LiteralPath (Join-Path $WorkRoot 'windows-deps\sdl') -Recurse -ErrorAction SilentlyContinue -Filter SDL2.dll |
    Where-Object { $_.FullName -match '\\lib\\x64\\SDL2\.dll$' } |
    Select-Object -First 1
$FfmpegDll = Get-ChildItem -LiteralPath (Join-Path $WorkRoot 'windows-deps\ffmpeg') -Recurse -ErrorAction SilentlyContinue -Filter avcodec*.dll |
    Select-Object -First 1

# restore-windows-dependencies.ps1 places the runtime DLLs in work\windows-sdk\bin.
$SdkBin = Join-Path $WorkRoot 'windows-sdk\bin'
if ($null -eq $SdlDll -and (Test-Path -LiteralPath (Join-Path $SdkBin 'SDL2.dll'))) { $SdlDll = Get-Item -LiteralPath (Join-Path $SdkBin 'SDL2.dll') }
if ($null -eq $FfmpegDll) { $FfmpegDll = Get-ChildItem -LiteralPath $SdkBin -Filter avcodec*.dll -ErrorAction SilentlyContinue | Select-Object -First 1 }

if (!(Test-Path -LiteralPath $Exe -PathType Leaf)) { throw "Missing native executable: $Exe" }
if (!(Test-Path -LiteralPath $Boot -PathType Leaf)) { throw "Missing verified BOOT.BIN: $Boot" }
if (!(Test-Path -LiteralPath (Join-Path $Disc 'PSP_GAME\USRDIR') -PathType Container)) { throw "Missing extracted disc root: $Disc" }
if ($null -eq $SdlDll) { throw "Missing SDL2 x64 DLL under work\windows-deps\sdl" }
if ($null -eq $FfmpegDll) { throw "Missing FFmpeg DLLs under work\windows-deps\ffmpeg" }

$SdlBin = $SdlDll.DirectoryName
$FfmpegBin = $FfmpegDll.DirectoryName
$env:PATH = "$SdlBin;$FfmpegBin;$env:PATH"

# Window/audio/runtime defaults for normal interactive play.
$env:PSPRECOMP_WINDOW = '1'
$env:PSPRECOMP_AUDIO = '1'
$env:PSPRECOMP_FRAME_LIMIT = '1'
$env:PSPRECOMP_RASTER_THREADS = '1'
$GpuPreview = $Renderer -ne 'Software'
$PcMode = $Renderer -eq 'PC'
$env:PSPRECOMP_GE_BACKEND = if ($GpuPreview) { 'directx12' } else { 'software' }
$env:PSPRECOMP_CONFIG = Join-Path $WorkRoot $(if ($GpuPreview) { 'rendering/dx12-preview.ini' } else { 'rendering/software.ini' })
$env:PSPRECOMP_DX12_GE_READBACK = if ($GpuPreview -and !$PcMode) { '1' } else { '0' }
$env:PSPRECOMP_DX12_GE_STRICT = if ($GpuPreview) { '1' } else { '0' }
$env:PSPRECOMP_GE_GPU_SKIP_SOFTWARE_RASTER = if ($PcMode) { '1' } else { '0' }
$env:PSPRECOMP_GE_GPU_HW_TRANSFORM = if ($PcMode) { '1' } else { '0' }
# PC mode: the game's own frame cap raised from the PSP's 20 fps, and the Asura-PC-derived lighting.
$env:RENEGADE_FRAME_RATE_CAP = if ($PcMode) { $FrameRateCap.ToString([Globalization.CultureInfo]::InvariantCulture) } else { '0' }
$env:RENEGADE_PER_PIXEL_LIGHTING = if ($PcMode -and !$NoPerPixelLighting) { '1' } else { '0' }
$env:RENEGADE_BLOOM = if ($PcMode -and !$NoBloom) { '1' } else { '0' }
$env:RENEGADE_SHADOWS = if ($PcMode -and !$NoShadows -and !$NoPerPixelLighting) { '1' } else { '0' }
$env:RENEGADE_FOG_CURVE = if ($PcMode -and $SmoothFog) { 'smooth' } else { 'linear' }
$env:PSPRECOMP_GE_GPU_HW_CULL = '0'
$env:RENEGADE_OUTPUT_RESOLUTION = $Resolution
$env:RENEGADE_HD_CAPTURE = if ($NativeRendering -or $GpuPreview) { '0' } else { '1' }
$env:RENEGADE_HD_PRESENT = if ($NativeRendering -or $GpuPreview) { '0' } else { '1' }
$env:RENEGADE_HD_START_VBLANK = '0'
$env:RENEGADE_FXAA = if ($NoFXAA -or $PcMode) { '0' } else { '1' }
$env:RENEGADE_HD_SURFACE_TEXTURES = if ($ExperimentalHDComposition) { '1' } else { '0' }

# Explicit pack selection per launch. Do not inherit a previous diagnostic run.
foreach ($Variable in @('RENEGADE_OVERRIDE_ROOT', 'RENEGADE_DUMP_TEXTURES', 'RENEGADE_TEXTURE_INSPECT', 'RENEGADE_RENDER_REPORT', 'RENEGADE_RENDER_START_VBLANK',
    'RENEGADE_TRACE_MODELS', 'RENEGADE_TRACE_RENDER_RESOURCES', 'RENEGADE_TRACE_MODEL_DRAWS', 'RENEGADE_TRACE_MODEL_TRANSFORMS', 'RENEGADE_TRACE_MODEL_SUBMISSIONS', 'RENEGADE_TRACE_COMMAND_POSES',
    'RENEGADE_WORLD_GEOMETRY','RENEGADE_WORLD_REPORT','RENEGADE_TRACE_WORLD_DRAWS','RENEGADE_TRACE_WORLD_VBLANK','RENEGADE_TRACE_WORLD_FULL')) {
    [Environment]::SetEnvironmentVariable($Variable, $null, 'Process')
}
if ($SelectedPack) { $env:RENEGADE_OVERRIDE_ROOT = $SelectedPack }
if ($InspectTextures) {
    $env:RENEGADE_TEXTURE_INSPECT = '1'
    $ReportDirectory = Join-Path $WorkRoot 'render-reports'
    if (!$DryRun) { New-Item -ItemType Directory -Path $ReportDirectory -Force | Out-Null }
    $env:RENEGADE_RENDER_REPORT = Join-Path $ReportDirectory ((Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8) + '.jsonl')
}
if (!$NoTextureDump) {
    $DumpPath = if ([IO.Path]::IsPathRooted($TextureDumpDirectory)) { $TextureDumpDirectory } else { Join-Path $RepoRoot $TextureDumpDirectory }
    if (!$DryRun) { New-Item -ItemType Directory -Path $DumpPath -Force | Out-Null }
    $env:RENEGADE_DUMP_TEXTURES = $DumpPath
}
$DiscoveryRoot = $null
if ($DiscoverAssets) {
    $DiscoveryName = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8)
    $DiscoveryRoot = Join-Path $WorkRoot (Join-Path 'override-discovery' $DiscoveryName)
    if (!$DryRun) { New-Item -ItemType Directory -Path $DiscoveryRoot -Force | Out-Null }
    $env:RENEGADE_DUMP_TEXTURES = Join-Path $DiscoveryRoot 'textures'
    $env:RENEGADE_TRACE_RENDER_RESOURCES = Join-Path $DiscoveryRoot 'models.jsonl'
}

# SDL controller hints. The native host samples SDL's GameController API; these
# keep Xbox-compatible/XInput pads enabled before SDL initializes.
$env:SDL_XINPUT_ENABLED = '1'
$env:SDL_JOYSTICK_RAWINPUT = '1'
$env:SDL_JOYSTICK_RAWINPUT_CORRELATE_XINPUT = '1'
$env:SDL_JOYSTICK_HIDAPI_XBOX = '1'
$env:SDL_JOYSTICK_HIDAPI_XBOX_360 = '1'
$env:SDL_JOYSTICK_HIDAPI_XBOX_ONE = '1'

# Renegade's modern profile: left stick movement, right stick look, triggers
# for shooter-style actions, with XInput-derived default deadzones.
$env:RENEGADE_CONTROLS = $Controls
$env:RENEGADE_LEFT_DEADZONE = $LeftDeadzone.ToString([Globalization.CultureInfo]::InvariantCulture)
$env:RENEGADE_RIGHT_DEADZONE = $RightDeadzone.ToString([Globalization.CultureInfo]::InvariantCulture)
$env:RENEGADE_LOOK_X = $LookX.ToString([Globalization.CultureInfo]::InvariantCulture)
$env:RENEGADE_LOOK_Y = $LookY.ToString([Globalization.CultureInfo]::InvariantCulture)
$env:RENEGADE_LOOK_CURVE = $LookCurve.ToString([Globalization.CultureInfo]::InvariantCulture)
$env:RENEGADE_TRIGGER_THRESHOLD = $TriggerThreshold.ToString([Globalization.CultureInfo]::InvariantCulture)
$env:RENEGADE_INVERT_Y = if ($InvertY) { '1' } else { '0' }

Write-Host "Renegade Squadron PC"
Write-Host "  Executable: $Exe"
Write-Host "  Disc root:  $Disc"
Write-Host "  Controls:   $env:RENEGADE_CONTROLS"
Write-Host "  XInput:     SDL_XINPUT_ENABLED=$env:SDL_XINPUT_ENABLED"
Write-Host "  Resolution: $env:RENEGADE_OUTPUT_RESOLUTION"
Write-Host "  Rendering:  $(if ($NativeRendering) { 'PSP native' } else { '1280x720 internal' }); FXAA=$env:RENEGADE_FXAA"
Write-Host "  Renderer:   $Renderer$(if ($PcMode) { "; 4x MSAA; cap $FrameRateCap fps; lighting=$env:RENEGADE_PER_PIXEL_LIGHTING bloom=$env:RENEGADE_BLOOM shadows=$env:RENEGADE_SHADOWS fog=$env:RENEGADE_FOG_CURVE" } elseif ($GpuPreview) { ' preview; MSAA up to 4x; texture-only packs' })"
Write-Host "  Textures:   $(if ($env:RENEGADE_DUMP_TEXTURES) { $env:RENEGADE_DUMP_TEXTURES } else { 'Dumping disabled' })"
Write-Host "  Overrides:  $(if ($SelectedPack) { $SelectedPack } else { 'Off (original assets)' })"
if ($DiscoveryRoot) {
    Write-Host "  Discovery:  $DiscoveryRoot"
    Write-Host "  Asset discovery is enabled and may slow gameplay. Close the game after capturing the assets you need."
}
Write-Host "  Mapping:    LS move/strafe, RS look, RT fire, LT lock/focus, A jump, L3 sprint"

if ($DryRun) {
    Write-Host "Dry run only; launch settings validated."
    exit 0
}

& $Exe $Boot $Disc $DispatchBudget
exit $LASTEXITCODE
