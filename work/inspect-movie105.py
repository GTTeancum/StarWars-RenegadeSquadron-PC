"""Verify and losslessly package an observed native/HD controller boundary."""
import hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parent.parent;name='campaign105-movie-parity-gpu'
control=root/'work/runs'/('control-'+name)
s=json.loads((control/'status.json').read_text());assert s['paused']
sequence=s['sequence'];frame=s['vblank'];dest=control/f'status_{sequence}_vblank_{frame}.json'
if dest.exists():assert json.loads(dest.read_text())==s
else:dest.write_text(json.dumps(s,indent=2)+'\n')
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
artifacts=[dest];images=[]
if s['gpu_capture']:
 assert s['gpu_source_vblank']==frame and (s['gpu_width'],s['gpu_height'])==(1280,720)
 assert s['gpu_frame'] and s['gpu_fxaa_frame']
else:assert not s['gpu_frame'] and not s['gpu_fxaa_frame']
for field in ['frame','gpu_frame','gpu_fxaa_frame']:
 if not s.get(field):continue
 p=control/s[field];assert p.parent==control
 im=Image.open(p).convert('RGB');expected=(480,272) if field=='frame' else (1280,720)
 assert im.size==expected
 png=root/'outputs'/f'{name}-{sequence}-{frame}-{field}.png'
 if not png.exists():im.save(png)
 assert np.array_equal(np.asarray(im),np.asarray(Image.open(png)))
 images.append(png.relative_to(root).as_posix());artifacts += [p,png]
report=dict(sequence=sequence,vblank=frame,gpu_capture=s['gpu_capture'],gpu_source_vblank=s['gpu_source_vblank'],
            images=images,scope='Actual native480x272 and same-boundary GPU1280x720 output, no resampling; not mission acceptance.',
            artifact_sha256={p.relative_to(root).as_posix():sha(p) for p in artifacts})
p=root/'outputs'/f'PAUSE-105-{sequence}-{frame}.json'
if p.exists():assert json.loads(p.read_text())==report
else:p.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='artifact_sha256'},indent=2))
