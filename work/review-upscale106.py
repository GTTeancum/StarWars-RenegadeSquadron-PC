"""Prepare repeatable visual QA samples; sheet is not an all-image art review."""
import hashlib, io, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
root=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
report=json.loads((root/'outputs/TEXTURE-PACK-106-ui2.json').read_text())
rows={r['id']:r for r in report['files']}
pilot=json.loads((root/'outputs/UPSCALER-106-pilot-plan.json').read_text())['inputs']
groups={'pilot':[(r['token'],rows[r['id']]) for r in pilot]}
world=[r for r in rows.values() if r['method']=='real_esrnet4x_fidelity_blend']
ranked=sorted(world,key=lambda r:r['source_fidelity']['rgb_p99'],reverse=True)
rejected=[r for r in world if r.get('effective_method')=='integer4x_fidelity_rejection']
groups['stress']=[('highest p99',r) for r in ranked[:4]]+[('fidelity rejected',r) for r in rejected[:2]]
partial=[r for r in world if not r.get('effective_method')]
def load(p):
 b=p.read_bytes();return Image.open(io.BytesIO(b+bytes(max(0,26-len(b))))).convert('RGBA')
for r in partial:
 alpha=np.asarray(load(root/r['original']))[:,:,3]
 if alpha.min()<255 and alpha.max()>0:
  groups['stress'].append(('partial alpha',r))
  if len(groups['stress'])>=8:break
receipts=[]
for name,items in groups.items():
 sheet=Image.new('RGB',(1024,288*((len(items)+1)//2)),(30,30,30));draw=ImageDraw.Draw(sheet)
 for index,(label,r) in enumerate(items):
  x=(index%2)*512;y=(index//2)*288
  original=load(root/r['original']);final=load(root/r['replacement'])
  for offset,im,mode in [(0,original,Image.Resampling.NEAREST),(256,final,Image.Resampling.LANCZOS)]:
   scale=min(256/im.width,256/im.height)
   im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),mode)
   background=Image.new('RGBA',(256,256),(80,80,80,255));background.alpha_composite(im,((256-im.width)//2,(256-im.height)//2));sheet.paste(background.convert('RGB'),(x+offset,y+32))
  draw.text((x+4,y+2),label+' | source / final',fill='white')
  draw.text((x+4,y+16),'NN '+str(round(r.get('neural_weight',0),3))+' | '+r['id'][7:23],fill='white')
 p=root/'outputs'/f'UPSCALER-106-final-{name}-qa.png';sheet.save(p)
 receipts.append(dict(group=name,file=p.relative_to(root).as_posix(),sha256=sha(p),ids=[r['id'] for _,r in items]))
(root/'outputs/UPSCALER-106-visual-samples.json').write_text(json.dumps(dict(samples=receipts,scope='Repeatable representative samples; human visual findings recorded separately. Not every-image artistic certification.'),indent=2)+'\n')
print(json.dumps(receipts,indent=2))
