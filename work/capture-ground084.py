"""Replay a selected ground map using the visually observed Yavin menu route."""
import argparse,json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
maps={'boz':0,'endor':1,'geonosis':2,'hoth':3,'echo':4,'kashyyyk':5,'korriban':6,'mustafar':7,'mygeeto':8,'naboo':9,'ordmantell':10,'saleucami':11,'sullust':12,'tatooine':13,'yavin':14}
p=argparse.ArgumentParser();p.add_argument('map',choices=maps);p.add_argument('--original',action='store_true');a=p.parse_args();index=maps[a.map]
rows=json.loads((root/'work/ground-map-menu072.json').read_text())['steps']
remove_start=1688+index*16
removed=[s for s in rows if remove_start<=s['start']<1912]
assert len(removed)==(14-index)*2 and all(s['psp'] in [0,64] for s in removed)
rows=[s for s in rows if not remove_start<=s['start']<1912]
text=(root/'work/instant015-boot.txt').read_text().rstrip()+'\n';frame=1400
for s in rows:
 end=frame+s['frames'];text+=f"{frame+1} {end} {s['psp']} {s['psp_x']} {s['psp_y']}\n";frame=end
for frames,buttons in [(184,0),(12,16384),(120,0),(12,16384),(240,0)]:
 end=frame+frames;text+=f'{frame+1} {end} {buttons} 128 128\n';frame=end
name='coverage084-'+a.map+('-original' if a.original else '');replay=root/'work'/f'{name}-replay.txt'
if replay.exists():assert replay.read_text()==text
else:replay.write_text(text)
cmd=[sys.executable,str(root/'work/project/tools/run010.py'),name,'--exe','work/build-windows-native/bin/RenegadeNative.exe','--root','work','--dll-dir','work/windows-sdk/bin','--isolate-executable','--vblanks',str(frame),'--timeout','900','--start',str(frame-1),'--stride','120','--replay',str(replay)]
env={'PSPRECOMP_FRAME_LIMIT':'0','PSPRECOMP_RASTER_THREADS':'1','PSPRECOMP_GE_BACKEND':'software','RENEGADE_HD_CAPTURE':'1','RENEGADE_HD_START_VBLANK':str(frame-15),'RENEGADE_FXAA':'1','RENEGADE_OVERRIDE_ROOT':str(root/'work/mods-textures-source074'),'RENEGADE_DUMP_TEXTURES':str(root/'work/runs'/name/'textures')}
if a.original:env.pop('RENEGADE_OVERRIDE_ROOT')
env['RENEGADE_TRACE_RENDER_RESOURCES']=str(root/'work/runs'/name/'resources.jsonl')
env['RENEGADE_TRACE_WORLD_DRAWS']=str(root/'work/runs'/name/'world-draws.jsonl')
env['RENEGADE_TRACE_WORLD_VBLANK']=str(frame-2)
for k,v in env.items():cmd+=['--env',f'{k}={v}']
raise SystemExit(subprocess.call(cmd,cwd=root))



