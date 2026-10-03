"""Bounded Instant Action inputs using the retained observed ground-menu route.

No guest state injection or archive substitution. New planet positions remain
provisional until actual menu images and archive-open logs confirm selection.
"""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
planets = {'boz':0,'endor':1,'geonosis':2,'hoth':3,'echo':4,'kashyyyk':5,
           'korriban':6,'mustafar':7,'mygeeto':8,'naboo':9,'ordmantell':10,
           'saleucami':11,'sullust':12,'tatooine':13,'yavin':14,
           'space-alderaan':15,'space-coruscant':16,'space-hoth':17,
           'space-kashyyyk':18,'space-kessel':19,'space-mygeeto':20,'space-yavin':21}
parser = argparse.ArgumentParser()
parser.add_argument('planet',choices=planets)
parser.add_argument('--name',required=True)
parser.add_argument('--era',choices=['gcw','clone'],default='gcw')
parser.add_argument('--renderer',choices=['software','gpu'],default='software')
parser.add_argument('--menu-only',action='store_true')
parser.add_argument('--menu-stage',choices=['planet','mode','era'])
parser.add_argument('--mode-index',type=int,choices=range(4),default=0)
parser.add_argument('--pack',choices=['source074','upscale106','upscale106-ui2','enhanced107'],required=True)
args = parser.parse_args()
if args.pack=='upscale106':assert (root/'outputs/TEXTURE-PACK-106.json').exists(),'Finish and verify the fallback pack first'
if args.pack=='upscale106-ui2':assert (root/'outputs/UPSCALER-106-ui2-verification.json').exists(),'Verify the corrected pack first'
if args.pack=='enhanced107':assert (root/'outputs/UPSCALER-107-verification.json').exists(),'Verify the enhanced pack first'
assert all(c.isalnum() or c in '-_' for c in args.name)
rows = json.loads((root/'work/ground-map-menu072.json').read_text())['steps']
rows = [r for r in rows if r['end'] <= 1688]
assert rows[0]['start'] == 1400 and rows[-1]['end'] == 1688
steps = [(r['frames'],r['psp'],r['psp_x'],r['psp_y']) for r in rows]
def tap(button,release=8):
    steps.extend([(8,button,128,128),(release,0,128,128)])
for _ in range(planets[args.planet]):
    tap(64)
menu_stage = args.menu_stage or ('planet' if args.menu_only else None)
if menu_stage != 'planet':
    tap(16384,24)  # planet
    for _ in range(args.mode_index):
        tap(64)
    if menu_stage != 'mode':
        tap(16384,24)  # mode
        if args.era == 'clone':
            tap(64)
        if menu_stage != 'era':
            tap(16384,24)  # era
            for b in [32,64,64,16384]:
                tap(b)    # focus right, launch
            steps += [(184,0,128,128),(12,16384,128,128),(120,0,128,128),
                      (12,16384,128,128),(360,0,128,128)]
if menu_stage:
    steps += [(48,0,128,128)]  # allow menu transition to finish before capture
frame = 1400
text = (root/'work/instant015-boot.txt').read_text().rstrip()+'\n'
records=[]
for frames,button,x,y in steps:
    end=frame+frames
    text+=f'{frame+1} {end} {button} {x} {y}\n'
    records.append(dict(start=frame+1,end=end,buttons=button,psp_x=x,psp_y=y))
    frame=end
replay=root/'work'/f'{args.name}-replay.txt'
assert not (root/'work/runs'/args.name).exists(), 'Run names are immutable; use a new name'
if replay.exists():
    assert replay.read_text()==text
else:
    replay.write_text(text)
meta=dict(texture_pack=args.pack,planet=args.planet,planet_index=planets[args.planet],era_requested=args.era,
          mode_index_requested=args.mode_index,renderer=args.renderer,menu_only=bool(menu_stage),menu_stage=menu_stage,
          menu_route_source='ground-map-menu072 prefix and controller taps only',
          planet_position_scope='Observed indices 0..20 in retained menu evidence; 21 requires fresh menu validation',
          replay_sha256=hashlib.sha256(replay.read_bytes()).hexdigest(),final_vblank=frame,
          capture_vblank=frame-1,steps=records,selection_verified=False)
(root/'work'/f'{args.name}-plan.json').write_text(json.dumps(meta,indent=2)+'\n')
env={'PSPRECOMP_WINDOW':'0','PSPRECOMP_FRAME_LIMIT':'0','PSPRECOMP_RASTER_THREADS':'1',
     'PSPRECOMP_GE_BACKEND':'directx12' if args.renderer=='gpu' else 'software',
     'PSPRECOMP_CONFIG':str(root/'work/rendering'/('dx12-preview.ini' if args.renderer=='gpu' else 'software.ini')),
     'RENEGADE_OUTPUT_RESOLUTION':'1280x720','RENEGADE_FXAA':'1',
     'RENEGADE_HD_CAPTURE':'0' if args.renderer=='gpu' else '1',
     'RENEGADE_HD_PRESENT':'0' if args.renderer=='gpu' else '1',
     'RENEGADE_HD_START_VBLANK':str(frame-15),
     'RENEGADE_RENDER_REPORT':str(root/'work/runs'/args.name/'render-report.jsonl'),
     'RENEGADE_RENDER_START_VBLANK':str(frame-15),
     'RENEGADE_OVERRIDE_ROOT':str(root/({'source074':'work/mods-textures-source074','upscale106':'work/mods-upscale106','upscale106-ui2':'work/mods-upscale106-ui2','enhanced107':'work/mods-enhanced107'}[args.pack])),
     'RENEGADE_DUMP_TEXTURES':str(root/'work/runs'/args.name/'textures'),
     'RENEGADE_HD_SURFACE_TEXTURES':'0','PSPRECOMP_GE_GPU_SKIP_SOFTWARE_RASTER':'0',
     'PSPRECOMP_GE_GPU_HW_TRANSFORM':'0','PSPRECOMP_GE_GPU_HW_CULL':'0'}
if args.renderer=='gpu':
    env.update(PSPRECOMP_DX12_GE_STRICT='1',PSPRECOMP_DX12_GE_READBACK='1',
               PSPRECOMP_GE_GPU_DUMP_VBLANK=str(frame-1),
               PSPRECOMP_GE_GPU_DUMP_PATH=str(root/'work/runs'/args.name/'gpu.ppm'))
cmd=[sys.executable,str(root/'work/project/tools/run010.py'),args.name,
     '--exe','work/build-windows-native/bin/RenegadeNative.exe','--root','work',
     '--dll-dir','work/windows-sdk/bin','--isolate-executable','--vblanks',str(frame),
     '--timeout','900','--start',str(frame-1),'--stride','120','--replay',str(replay)]
for key,value in env.items():
    cmd+=['--env',f'{key}={value}']
print(json.dumps({k:v for k,v in meta.items() if k!='steps'},indent=2),flush=True)
raise SystemExit(subprocess.call(cmd,cwd=root))
