"""Derive Korriban GCW Conquest replay from the observed Yavin menu route."""
import json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
rows=[json.loads(s) for s in (root/'work/runs/control-source065-yavin/adaptive011.jsonl').read_text().splitlines()]
rows=[s for s in rows if s['end']<=2072]
removed=[s for s in rows if 1784<=s['start']<1912]
assert len(removed)==16 and all(s['psp'] in [0,64] for s in removed)
rows=[s for s in rows if not 1784<=s['start']<1912]
text=(root/'work/instant015-boot.txt').read_text().rstrip()+'\n';frame=1400
for s in rows:
 end=frame+s['frames'];text+=f"{frame+1} {end} {s['psp']} {s['psp_x']} {s['psp_y']}\n";frame=end
for frames,buttons in [(184,0),(12,16384),(120,0),(12,16384),(240,0)]:
 end=frame+frames;text+=f'{frame+1} {end} {buttons} 128 128\n';frame=end
replay=root/'work/source067-korriban-replay.txt'
if replay.exists():assert replay.read_text()==text
else:replay.write_text(text)
cmd=[sys.executable,str(root/'work/project/tools/run010.py'),'source067-korriban','--exe','work/build-windows-native/bin/RenegadeNative.exe','--root','work','--dll-dir','work/windows-sdk/bin','--isolate-executable','--vblanks',str(frame),'--timeout','600','--start',str(frame-1),'--stride','120','--replay',str(replay)]
env={'PSPRECOMP_FRAME_LIMIT':'0','PSPRECOMP_RASTER_THREADS':'1','PSPRECOMP_GE_BACKEND':'software','RENEGADE_HD_CAPTURE':'1','RENEGADE_HD_START_VBLANK':str(frame-15),'RENEGADE_FXAA':'1','RENEGADE_OVERRIDE_ROOT':str(root/'work/mods-textures-source067'),'RENEGADE_DUMP_TEXTURES':str(root/'work/runs/source067-korriban/textures')}
for k,v in env.items():cmd+=['--env',f'{k}={v}']
raise SystemExit(subprocess.call(cmd,cwd=root))
