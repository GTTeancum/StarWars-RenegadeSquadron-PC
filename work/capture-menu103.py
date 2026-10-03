"""Normal cold-boot single-player branches; probe menus before choosing missions."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser();p.add_argument('branch',choices=['single','campaign','gc'])
p.add_argument('--name',required=True);p.add_argument('--confirm-count',type=int,choices=range(6),default=0)
p.add_argument('--choice',type=int,choices=range(8),default=0)
p.add_argument('--horizontal-choice',action='store_true')
p.add_argument('--after-button',type=lambda s:int(s,0),default=0,help='One observed menu action after branch confirmations')
p.add_argument('--renderer',choices=['software','gpu'],default='software')
a=p.parse_args();assert all(c.isalnum() or c in '-_' for c in a.name)
assert 0<=a.after_button<=0x3ffff
rows=json.loads((root/'work/ground-map-menu072.json').read_text())['steps']
rows=[r for r in rows if r['end']<=1448]
assert len(rows)==2 and rows[0]['start']==1400 and rows[-1]['end']==1448
steps=[(r['frames'],r['psp'],r['psp_x'],r['psp_y']) for r in rows]
def tap(button,release=8):steps.extend([(8,button,128,128),(release,0,128,128)])
if a.branch!='single':
    for _ in range(1 if a.branch=='campaign' else 2):tap(64)
    tap(16384,40)
    for _ in range(a.choice):tap(32 if a.horizontal_choice else 64)
    for _ in range(a.confirm_count):tap(16384,40)
    if a.after_button:tap(a.after_button,40)
steps.append((80,0,128,128))
frame=1400;text=(root/'work/instant015-boot.txt').read_text().rstrip()+'\n';records=[]
for frames,button,x,y in steps:
    end=frame+frames;text+=f'{frame+1} {end} {button} {x} {y}\n'
    records.append(dict(start=frame+1,end=end,buttons=button,psp_x=x,psp_y=y));frame=end
replay=root/'work'/f'{a.name}-replay.txt'
assert not (root/'work/runs'/a.name).exists(),'Run names are immutable'
if replay.exists():assert replay.read_text()==text
else:replay.write_text(text)
meta=dict(branch_requested=a.branch,confirm_count=a.confirm_count,choice=a.choice,horizontal_choice=a.horizontal_choice,after_button=a.after_button,
          renderer=a.renderer,final_vblank=frame,capture_vblank=frame-1,steps=records,
          menu_route_source='Observed historical source065 Single Player menu; fresh actual capture determines current options',
          replay_sha256=hashlib.sha256(replay.read_bytes()).hexdigest(),selection_verified=False)
(root/'work'/f'{a.name}-plan.json').write_text(json.dumps(meta,indent=2)+'\n')
gpu=a.renderer=='gpu'
env={'PSPRECOMP_WINDOW':'0','PSPRECOMP_FRAME_LIMIT':'0','PSPRECOMP_RASTER_THREADS':'1',
     'PSPRECOMP_GE_BACKEND':'directx12' if gpu else 'software',
     'PSPRECOMP_CONFIG':str(root/'work/rendering'/('dx12-preview.ini' if gpu else 'software.ini')),
     'RENEGADE_OUTPUT_RESOLUTION':'1280x720','RENEGADE_FXAA':'1',
     'RENEGADE_HD_CAPTURE':'0' if gpu else '1','RENEGADE_HD_PRESENT':'0' if gpu else '1',
     'RENEGADE_HD_START_VBLANK':str(frame-15),'RENEGADE_RENDER_START_VBLANK':str(frame-15),
     'RENEGADE_RENDER_REPORT':str(root/'work/runs'/a.name/'render-report.jsonl'),
     'RENEGADE_OVERRIDE_ROOT':str(root/'work/mods-textures-source074'),
     'RENEGADE_DUMP_TEXTURES':str(root/'work/runs'/a.name/'textures'),
     'RENEGADE_HD_SURFACE_TEXTURES':'0','PSPRECOMP_GE_GPU_SKIP_SOFTWARE_RASTER':'0',
     'PSPRECOMP_GE_GPU_HW_TRANSFORM':'0','PSPRECOMP_GE_GPU_HW_CULL':'0'}
if gpu:
    env.update(PSPRECOMP_DX12_GE_STRICT='1',PSPRECOMP_DX12_GE_READBACK='1',
               PSPRECOMP_GE_GPU_DUMP_VBLANK=str(frame-1),
               PSPRECOMP_GE_GPU_DUMP_PATH=str(root/'work/runs'/a.name/'gpu.ppm'))
cmd=[sys.executable,str(root/'work/project/tools/run010.py'),a.name,
     '--exe','work/build-windows-native/bin/RenegadeNative.exe','--root','work',
     '--dll-dir','work/windows-sdk/bin','--isolate-executable','--vblanks',str(frame),
     '--timeout','900','--start',str(frame-1),'--stride','120','--replay',str(replay)]
for k,v in env.items():cmd+=['--env',f'{k}={v}']
print(json.dumps({k:v for k,v in meta.items() if k!='steps'},indent=2),flush=True)
raise SystemExit(subprocess.call(cmd,cwd=root))
