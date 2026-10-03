"""Confirm clean/enhanced collages contain accepted captures without modification."""
import hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parent.parent;out=root/'outputs';sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest();rows=[]
for scenario in ['mygeeto-clone','hoth-gcw','space-kashyyyk-gcw']:
 pair=out/f'UPSCALER-107-{scenario}-comparison.png';before=out/f'textures106-{scenario}-after-ui2-gpu-fxaa.png';after=out/f'textures107-{scenario}-gpu-fxaa.png';a=np.asarray(Image.open(pair));assert a.shape==(744,2560,3) and np.array_equal(a[24:,:1280],np.asarray(Image.open(before))) and np.array_equal(a[24:,1280:],np.asarray(Image.open(after)))
 rows.append(dict(scenario=scenario,unchanged_capture_pixels=1280*720*2,sha256={p.relative_to(root).as_posix():sha(p) for p in [pair,before,after]}))
report=dict(comparisons=rows,scope='Pixel-exact clean/enhanced collage assembly with24px labels. Fresh actor timing is not deterministic; raw texture sheets provide direct asset comparison.')
p=out/'UPSCALER-107-comparison-verification.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n');print('Three comparison collages verified')
