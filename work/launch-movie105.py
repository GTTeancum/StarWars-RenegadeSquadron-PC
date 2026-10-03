"""Reproduce104's normal menu restart, now verify CPU movie GPU presentation."""
import hashlib,json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent;name='campaign105-movie-parity-gpu'
control=root/'work/runs'/('control-'+name)
assert not control.exists() and not (root/'work/runs'/name).exists()
control.mkdir();pad=control/'gamepad.txt';pad.write_text('1 0 0 0 0 0 0 0 0\n')
boot=root/'work/project/replays/controls008-boot-to-spawn.txt'
records=[json.loads(s) for s in (root/'work/runs/control-campaign104-modern-guided-gpu/adaptive104.jsonl').read_text().splitlines()]
lines=boot.read_text().splitlines()
for r in records:
 if r['sequence']>16:break
 # Legacy/menu inputs only. The earlier diagnostic raw movement is omitted;
 # the menu restart resets the mission before the movie under test.
 lines.append(f"{r['start']+1} {r['until']} {r['psp']} {r['psp_x']} {r['psp_y']}")
replay=root/'work'/f'{name}-replay.txt';assert not replay.exists();replay.write_text('\n'.join(lines)+'\n')
env={'PSPRECOMP_WINDOW':'0','PSPRECOMP_FRAME_LIMIT':'0','PSPRECOMP_RASTER_THREADS':'1',
 'PSPRECOMP_GE_BACKEND':'directx12','PSPRECOMP_CONFIG':str(root/'work/rendering/dx12-preview.ini'),
 'RENEGADE_OUTPUT_RESOLUTION':'1280x720','RENEGADE_FXAA':'1','RENEGADE_HD_CAPTURE':'0','RENEGADE_HD_PRESENT':'0',
 'RENEGADE_OVERRIDE_ROOT':str(root/'work/mods-textures-source074'),
 'RENEGADE_DUMP_TEXTURES':str(root/'work/runs'/name/'textures'),'RENEGADE_HD_SURFACE_TEXTURES':'0',
 'PSPRECOMP_GE_GPU_SKIP_SOFTWARE_RASTER':'0','PSPRECOMP_GE_GPU_HW_TRANSFORM':'0','PSPRECOMP_GE_GPU_HW_CULL':'0',
 'PSPRECOMP_DX12_GE_STRICT':'1','PSPRECOMP_DX12_GE_READBACK':'1','PSPRECOMP_FRAME_TIME_DIAG':'1',
 'RENEGADE_CONTROLS':'modern','RENEGADE_TRACE_ACTIONS':'1','RENEGADE_TRACE_CONTEXTS':'1',
 'RENEGADE_GAMEPAD_DIAGNOSTIC':str(pad),'RENEGADE_CONTROL_DIRECTORY':str(control),'RENEGADE_CONTROL_START':'3146'}
meta=dict(name=name,start_pause=3146,maximum_vblank=6000,timeout_seconds=1800,
 replay_sha256=hashlib.sha256(replay.read_bytes()).hexdigest(),native_sha256=hashlib.sha256((root/'work/build-windows-native/bin/RenegadeNative.exe').read_bytes()).hexdigest(),
 scope='Ordinary menu restart inputs reproduced from104; raw movement omitted. Actual movie state must be observed, not inferred from timing. CPU-decoded movie upload only; no guest/gameplay/texture-source edits. Mip/filter changes skipped.')
(root/'work'/f'{name}-plan.json').write_text(json.dumps(meta,indent=2)+'\n')
cmd=[sys.executable,str(root/'work/project/tools/run010.py'),name,'--exe','work/build-windows-native/bin/RenegadeNative.exe',
 '--root','work','--dll-dir','work/windows-sdk/bin','--isolate-executable','--vblanks','6000','--timeout','1800',
 '--budget','5000000000','--start','1500','--stride','300','--replay',str(replay)]
for k,v in env.items():cmd+=['--env',f'{k}={v}']
print(json.dumps(meta,indent=2),flush=True)
raise SystemExit(subprocess.call(cmd,cwd=root))
