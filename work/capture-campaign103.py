"""Bounded current-build attempt at the preserved legacy campaign recording.

Historical Linux victory is not assumed to reproduce. Inputs only; no unlocks,
save edits, game positions or mission flags. Native intermediate frames retain
outcome evidence, while the final GPU view is a real 720p capture.
"""
import hashlib,json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
name='coverage103-yavin-campaign-recorded-gpu'
source=root/'work/checkpoint009/replays/yavin-first-victory007.txt'
replay=root/'work'/f'{name}-replay.txt';assert not replay.exists()
text=source.read_text().rstrip()+'\n'
for first,last,mask in [(13512,13519,16384),(13520,13759,0),
                        (13760,13767,16384),(13768,13963,0),
                        (13964,13971,16384),(13972,14191,0),
                        (14192,14199,16384),(14200,14511,0)]:
    text+=f'{first} {last} {mask} 128 128\n'
replay.write_text(text)
stop=14512
meta=dict(name=name,final_vblank=stop,capture_vblank=stop-1,renderer='gpu',
          input_scope='Preserved legacy PSP recording plus normal Cross/neutral continuation; not modern or deterministic acceptance.',
          original_recording=source.relative_to(root).as_posix(),
          original_recording_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
          replay_sha256=hashlib.sha256(replay.read_bytes()).hexdigest(),
          historical_only='Linux checkpoint007 victory at 13512; current outcome and second-mission opens must be inspected.',
          intermediate_capture_scope='480x272 software reference snapshots at 13512, 13962 and 14412; final GPU is actual 1280x720.')
(root/'work'/f'{name}-plan.json').write_text(json.dumps(meta,indent=2)+'\n')
env={'PSPRECOMP_WINDOW':'0','PSPRECOMP_FRAME_LIMIT':'0','PSPRECOMP_RASTER_THREADS':'1',
     'PSPRECOMP_GE_BACKEND':'directx12','PSPRECOMP_CONFIG':str(root/'work/rendering/dx12-preview.ini'),
     'RENEGADE_OUTPUT_RESOLUTION':'1280x720','RENEGADE_FXAA':'1','RENEGADE_HD_CAPTURE':'0','RENEGADE_HD_PRESENT':'0',
     'RENEGADE_RENDER_REPORT':str(root/'work/runs'/name/'render-report.jsonl'),
     'RENEGADE_RENDER_START_VBLANK':str(stop-15),
     'RENEGADE_OVERRIDE_ROOT':str(root/'work/mods-textures-source074'),
     'RENEGADE_DUMP_TEXTURES':str(root/'work/runs'/name/'textures'),
     'RENEGADE_HD_SURFACE_TEXTURES':'0','PSPRECOMP_GE_GPU_SKIP_SOFTWARE_RASTER':'0',
     'PSPRECOMP_GE_GPU_HW_TRANSFORM':'0','PSPRECOMP_GE_GPU_HW_CULL':'0',
     'PSPRECOMP_DX12_GE_STRICT':'1','PSPRECOMP_DX12_GE_READBACK':'1',
     'PSPRECOMP_GE_GPU_DUMP_VBLANK':str(stop-1),
     'PSPRECOMP_GE_GPU_DUMP_PATH':str(root/'work/runs'/name/'gpu.ppm')}
cmd=[sys.executable,str(root/'work/project/tools/run010.py'),name,
     '--exe','work/build-windows-native/bin/RenegadeNative.exe','--root','work',
     '--dll-dir','work/windows-sdk/bin','--isolate-executable','--vblanks',str(stop),
     '--timeout','2400','--budget','8000000000','--start','13512','--stride','450','--replay',str(replay)]
for k,v in env.items():cmd+=['--env',f'{k}={v}']
print(json.dumps(meta,indent=2),flush=True)
raise SystemExit(subprocess.call(cmd,cwd=root))
