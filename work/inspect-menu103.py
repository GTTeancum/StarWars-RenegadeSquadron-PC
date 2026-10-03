"""Verify a completed branch probe and encode its actual captures losslessly."""
import argparse,hashlib,json,re
from pathlib import Path
import numpy as np
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('name');a=p.parse_args()
root=Path(__file__).resolve().parent.parent;folder=root/'work/runs'/a.name
state=json.loads((folder/'run.json').read_text());assert state['state']=='finished' and state['exit_code']==0 and not state['timed_out']
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
assert sha(folder/'native/RenegadeNative.exe')==state['native_binary_sha256']=='924ae90a2ed8141bb418df07203100912bb08176eb987b3a834819a49a68e2ec'
env=state['environment'];stop=int(env['PSPRECOMP_STOP_VBLANK']);log=(folder/'native.log').read_text(errors='replace')
assert f'VBlank diagnostic stop at {stop} ' in log
assert env['PSPRECOMP_WINDOW']=='0' and env['RENEGADE_OUTPUT_RESOLUTION']=='1280x720' and env['RENEGADE_FXAA']=='1'
gpu=env['PSPRECOMP_GE_BACKEND']=='directx12'
raw=folder/'gpu.ppm' if gpu else folder/f'frames/render-720p/frame_{stop-1:06d}.ppm'
fxaa=folder/'gpu-fxaa.ppm' if gpu else folder/f'frames/render-720p-fxaa/frame_{stop-1:06d}.ppm'
paths=[]
for suffix,src in [('unfiltered',raw),('fxaa',fxaa)]:
    im=Image.open(src).convert('RGB');assert im.size==(1280,720)
    dest=root/'outputs'/f'{a.name}-{suffix}.png';im.save(dest)
    assert np.array_equal(np.asarray(im),np.asarray(Image.open(dest)));paths.append(dest)
opens=sorted({m[1].replace('\\','/') for line in log.splitlines() if '[io] raw UMD open' in line
              for m in [re.search(r'[\\/]((?:ENVS|GUIMENU|GRAPHICS|MISC)[\\/][^"\r\n]+)"',line)] if m})
report=dict(name=a.name,terminal_exit=0,timed_out=False,stop_vblank=stop,actual_opens=opens,
            scope='Terminal/capture/actual-open evidence only; menu options must be read from the actual image.',
            artifact_sha256={p.relative_to(root).as_posix():sha(p) for p in [folder/'run.json',folder/'native.log',raw,fxaa,*paths]})
(root/'outputs'/f'{a.name}-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='artifact_sha256'},indent=2))
