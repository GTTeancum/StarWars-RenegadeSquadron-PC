"""Verify final scene comparisons contain the untouched accepted capture pixels."""
import hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parent.parent;out=root/'outputs'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
records=[]
for scenario in ['mygeeto-clone','hoth-gcw','space-kashyyyk-gcw']:
 p=out/f'UPSCALER-106-{scenario}-comparison.png';pair=np.asarray(Image.open(p))
 before=out/f'textures106-{scenario}-before-gpu-fxaa.png';after=out/f'textures106-{scenario}-after-ui2-gpu-fxaa.png'
 assert pair.shape==(744,2560,3)
 assert np.array_equal(pair[24:,:1280],np.asarray(Image.open(before)))
 assert np.array_equal(pair[24:,1280:],np.asarray(Image.open(after)))
 records.append(dict(scenario=scenario,unchanged_capture_pixels=1280*720*2,artifact_sha256={v.relative_to(root).as_posix():sha(v) for v in [p,before,after]}))
report=dict(comparisons=records,
 visual_review='Final Mygeeto/Hoth/Space views inspected internally. Ground/space scene and HUD visible, limited detail smoothing; no assertion of a high-detail remaster. Sixteen pilot/stress sample pairs inspected: stone relief/grain retained, silhouettes/layout consistent, rejected cases exact; fonts/icons exact source pixels. All46 corrected UI images independently exact RGBA4x. Original alpha/channel/orientation audits are distinct from representative artistic review.',
 scope='Pixel-exact scene collage assembly with24px labels; no image alterations. Fresh runs may differ in actor timing. Complete per-asset artistic certification and original-PSP visual correctness remain unverified.')
p=out/'UPSCALER-106-comparison-verification.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n')
print('Three comparisons:5,529,600 capture pixels preserved exactly')
