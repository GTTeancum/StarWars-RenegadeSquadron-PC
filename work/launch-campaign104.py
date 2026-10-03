"""Fresh controller-guided campaign: bounded lifetime, early references, HD pauses."""
import hashlib,json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
name='campaign104-modern-guided-gpu';control=root/'work/runs'/('control-'+name)
assert not control.exists() and not (root/'work/runs'/name).exists(),'Do not relaunch an existing diagnostic'
control.mkdir();pad=control/'gamepad.txt';pad.write_text('1 0 0 0 0 0 0 0 0\n')
source=root/'work/project/replays/controls008-boot-to-spawn.txt'
replay=root/'work'/f'{name}-replay.txt';assert not replay.exists();replay.write_bytes(source.read_bytes())
meta=dict(name=name,start_pause=2524,maximum_vblank=20000,timeout_seconds=7200,
          source_replay=source.relative_to(root).as_posix(),replay_sha256=hashlib.sha256(replay.read_bytes()).hexdigest(),
          input_scope='Normal PSP menu inputs until2524; guided modern diagnostic raw pads and explicit PSP menu inputs after that. No game-state edits or physical XInput acceptance.',
          capture_scope='Actual same-boundary GPU HD and FXAA readbacks at controller pauses; native480x272 references retained. Stale/missing readback is explicitly uncaptured.',
          early_reference_scope='Native480x272 samples from1500 every300 vblanks; not enlarged HD screenshots.',
          first_mission_complete=False)
(root/'work'/f'{name}-plan.json').write_text(json.dumps(meta,indent=2)+'\n')
env={'PSPRECOMP_WINDOW':'0','PSPRECOMP_FRAME_LIMIT':'0','PSPRECOMP_RASTER_THREADS':'1',
 'PSPRECOMP_GE_BACKEND':'directx12','PSPRECOMP_CONFIG':str(root/'work/rendering/dx12-preview.ini'),
 'RENEGADE_OUTPUT_RESOLUTION':'1280x720','RENEGADE_FXAA':'1','RENEGADE_HD_CAPTURE':'0','RENEGADE_HD_PRESENT':'0',
 'RENEGADE_OVERRIDE_ROOT':str(root/'work/mods-textures-source074'),
 'RENEGADE_DUMP_TEXTURES':str(root/'work/runs'/name/'textures'),'RENEGADE_HD_SURFACE_TEXTURES':'0',
 'PSPRECOMP_GE_GPU_SKIP_SOFTWARE_RASTER':'0','PSPRECOMP_GE_GPU_HW_TRANSFORM':'0','PSPRECOMP_GE_GPU_HW_CULL':'0',
 'PSPRECOMP_DX12_GE_STRICT':'1','PSPRECOMP_DX12_GE_READBACK':'1','PSPRECOMP_FRAME_TIME_DIAG':'1',
 'RENEGADE_CONTROLS':'modern','RENEGADE_TRACE_ACTIONS':'1','RENEGADE_TRACE_CONTEXTS':'1',
 'RENEGADE_GAMEPAD_DIAGNOSTIC':str(pad),'RENEGADE_CONTROL_DIRECTORY':str(control),'RENEGADE_CONTROL_START':'2524'}
cmd=[sys.executable,str(root/'work/project/tools/run010.py'),name,'--exe','work/build-windows-native/bin/RenegadeNative.exe',
 '--root','work','--dll-dir','work/windows-sdk/bin','--isolate-executable','--vblanks','20000','--timeout','7200',
 '--budget','8000000000','--start','1500','--stride','300','--replay',str(replay)]
for k,v in env.items():cmd+=['--env',f'{k}={v}']
print(json.dumps(meta,indent=2),flush=True)
raise SystemExit(subprocess.call(cmd,cwd=root))
