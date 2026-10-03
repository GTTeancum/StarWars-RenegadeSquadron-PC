"""Replay the recorded Yavin GCW conquest spawn, enabling HD only at the end."""
import argparse,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--original',action='store_true');a=p.parse_args()
cmd=[sys.executable,str(root/'work/project/tools/run010.py'),a.name,'--exe','work/build-windows-native/bin/RenegadeNative.exe','--root','work','--dll-dir','work/windows-sdk/bin','--isolate-executable','--vblanks','2640','--timeout','600','--start','2639','--stride','120','--replay','work/source065-yavin-replay.txt']
env={'PSPRECOMP_FRAME_LIMIT':'0','PSPRECOMP_RASTER_THREADS':'1','PSPRECOMP_GE_BACKEND':'software','RENEGADE_HD_CAPTURE':'1','RENEGADE_HD_START_VBLANK':'2625','RENEGADE_FXAA':'1'}
if not a.original:env['RENEGADE_OVERRIDE_ROOT']=str(root/'work/mods-textures-source065')
env['RENEGADE_DUMP_TEXTURES']=str(root/'work/runs'/a.name/'textures')
for key,value in env.items():cmd+=['--env',f'{key}={value}']
raise SystemExit(subprocess.call(cmd,cwd=root))
