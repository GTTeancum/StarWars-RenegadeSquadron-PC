"""Review ESRGAN as a controlled detail layer over the clean checkpoint106 output."""
import hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
rows=json.loads((root/'outputs/UPSCALER-107-pilot-plan.json').read_text())['inputs']
sheet=Image.new('RGB',(1024,384*len(rows)),(28,28,28));draw=ImageDraw.Draw(sheet);samples=[]
for index,r in enumerate(rows):
 clean=Image.open(root/'work/mods-upscale106-ui2/textures'/(r['id']+'.png')).convert('RGBA')
 esr=Image.open(root/'work/upscale107/pilot/esrgan'/(r['id']+'.png')).convert('RGB');assert esr.size==clean.size
 alpha=clean.getchannel('A');a=np.asarray(clean.convert('RGB')).astype(float);b=np.asarray(esr).astype(float)
 variants=[('checkpoint106',clean)]
 for label,w in [('ESR detail35%',.35),('ESR detail55%',.55),('ESR detail75%',.75)]:
  rgb=Image.fromarray(np.clip(np.rint(a*(1-w)+b*w),0,255).astype('uint8')).convert('RGBA');rgb.putalpha(alpha);variants.append((label,rgb))
 y=index*384;draw.text((4,y+4),r['token']+' | '+r['id'][7:23],fill='white')
 for col,(label,im) in enumerate(variants):
  x=col*256;draw.text((x+4,y+20),label,fill='white');scale=min(256/im.width,344/im.height);shown=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
  bg=Image.new('RGBA',(256,344),(75,75,75,255));bg.alpha_composite(shown,((256-shown.width)//2,(344-shown.height)//2));sheet.paste(bg.convert('RGB'),(x,y+40))
 samples.append(dict(token=r['token'],id=r['id'],clean_sha256=sha(root/'work/mods-upscale106-ui2/textures'/(r['id']+'.png')),esrgan_sha256=sha(root/'work/upscale107/pilot/esrgan'/(r['id']+'.png'))))
dest=root/'outputs/UPSCALER-107-hybrid-comparison.png';sheet.save(dest)
(root/'outputs/UPSCALER-107-hybrid-comparison.json').write_text(json.dumps(dict(sheet_sha256=sha(dest),samples=samples,scope='Raw texture selection: checkpoint106 versus35/55/75percent ESRGAN detail layer. UI remains outside neural enhancement.'),indent=2)+'\n')
print(dest)
