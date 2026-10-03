param([Parameter(Mandatory=$true)][ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$Name)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$python='C:\Users\LRPC\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$args010=@(
    "$root/project/tools/run010.py",$Name,
    '--exe',"$root/build-windows-native/bin/RenegadeNative.exe",'--root',$root,
    '--dll-dir',"$root/windows-sdk/bin",'--isolate-executable',
    '--vblanks','50000','--timeout','7200','--start','1400','--stride','15',
    '--replay',"$root/project/replays/../../instant015-boot.txt",
    '--env','PSPRECOMP_FRAME_LIMIT=0','--env','PSPRECOMP_RASTER_THREADS=1',
    '--env','PSPRECOMP_GE_BACKEND=software','--env','RENEGADE_CONTROLS=modern',
    '--env','RENEGADE_TRACE_ACTIONS=1','--env','RENEGADE_TRACE_CONTEXTS=1',
    '--env',"RENEGADE_GAMEPAD_DIAGNOSTIC=$root/runs/gamepad-$Name.txt",
    '--env','RENEGADE_CONTROL_START=1400',
    '--env',"RENEGADE_CONTROL_DIRECTORY=$root/runs/control-$Name"
)
& $python @args010
exit $LASTEXITCODE

