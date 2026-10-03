"""Capture actual runtime texture identities through known Instant Action replays."""
import argparse,json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser();p.add_argument('scenario',choices=['boz','geonosis','coruscant','alderaan','echo','kashyyyk']);a=p.parse_args()
letter=dict(boz='a',geonosis='b',coruscant='c',alderaan='d',echo='e',kashyyyk='f')[a.scenario]
rows=[json.loads(s) for s in (root/f'work/runs/control-instant016{letter}/adaptive011.jsonl').read_text().splitlines()]
last=rows[-1]['end'];name='source066-'+a.scenario
replay=root/f'work/{name}-replay.txt'
text=(root/'work/instant015-boot.txt').read_text().rstrip()+'\n'
text+='\n'.join(f"{s['start']+1} {s['end']} {s['psp']} {s['psp_x']} {s['psp_y']}" for s in rows)+'\n'
if replay.exists():assert replay.read_text()==text
else:replay.write_text(text)
cmd=[sys.executable,str(root/'work/project/tools/run010.py'),name,'--exe','work/build-windows-native/bin/RenegadeNative.exe',
     '--root','work','--dll-dir','work/windows-sdk/bin','--isolate-executable','--vblanks',str(last),
     '--timeout','600','--start',str(last-1),'--stride','120','--replay',str(replay)]
env={'PSPRECOMP_FRAME_LIMIT':'0','PSPRECOMP_RASTER_THREADS':'1','PSPRECOMP_GE_BACKEND':'software',
     'RENEGADE_OVERRIDE_ROOT':str(root/'work/mods-textures-source066'),
     'RENEGADE_DUMP_TEXTURES':str(root/f'work/runs/{name}/textures'),
     'RENEGADE_HD_CAPTURE':'1','RENEGADE_HD_START_VBLANK':str(last-15),'RENEGADE_FXAA':'1'}
for k,v in env.items():cmd+=['--env',f'{k}={v}']
raise SystemExit(subprocess.call(cmd,cwd=root))
