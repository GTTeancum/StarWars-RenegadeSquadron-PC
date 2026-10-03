"""Build category and highest-detail raw-texture review sheets for pack107."""
import hashlib,json,random
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parent.parent;sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
pack=json.loads((root/'outputs/TEXTURE-PACK-107.json').read_text());enh=[r for r in pack['files'] if r.get('effective_method')=='esrgan_x4_detail55']
pilots={r['id'] for r in json.loads((root/'outputs/UPSCALER-107-pilot-plan.json').read_text())['inputs']}
bycat={c:[r for r in enh if r['category']==c] for c in pack['category_counts']};rng=random.Random(107)
chosen=[]
for r in enh:
 if r['id'] in pilots:chosen.append(('pilot',r))
for cat,rows in bycat.items():
 for r in sorted(rows,key=lambda x:x['high_frequency_ratio'],reverse=True)[:3]:chosen.append((cat+' high-frequency',r))
 for r in rng.sample(rows,min(2,len(rows))):chosen.append((cat+' deterministic sample',r))
seen=set();chosen=[v for v in chosen if not (v[1]['id'] in seen or seen.add(v[1]['id']))]
receipts=[]
for page in range((len(chosen)+7)//8):
 items=chosen[page*8:(page+1)*8];sheet=Image.new('RGB',(1024,320*((len(items)+1)//2)),(28,28,28));draw=ImageDraw.Draw(sheet)
 for i,(label,r) in enumerate(items):
  x=(i%2)*512;y=(i//2)*320;before=Image.open(root/'work/mods-upscale106-ui2/textures'/Path(r['replacement']).name).convert('RGBA');after=Image.open(root/r['replacement']).convert('RGBA')
  draw.text((x+4,y+3),label+' | clean106 / enhanced107',fill='white');draw.text((x+4,y+17),f"55% ESR | HF {r['high_frequency_ratio']:.2f} | {r['id'][7:19]}",fill='white')
  for offset,im in [(0,before),(256,after)]:
   scale=min(256/im.width,288/im.height);shown=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS);bg=Image.new('RGBA',(256,288),(75,75,75,255));bg.alpha_composite(shown,((256-shown.width)//2,(288-shown.height)//2));sheet.paste(bg.convert('RGB'),(x+offset,y+32))
 p=root/'outputs'/f'UPSCALER-107-raw-review-{page+1}.png';sheet.save(p);receipts.append(dict(file=p.relative_to(root).as_posix(),sha256=sha(p),ids=[r['id'] for _,r in items]))
report=dict(samples=len(chosen),pages=receipts,scope='Pilot, category, highest-frequency and deterministic raw-texture pairs. Human review required; not every-image artistic certification.')
# A dense sheet of the24 largest environment ratios catches low-energy sources
# where the relative metric can expose either desirable grain or false hatching.
outliers=sorted(bycat['environment_surface'],key=lambda r:r['high_frequency_ratio'],reverse=True)[:24]
sheet=Image.new('RGB',(1024,192*len(outliers)),(28,28,28));draw=ImageDraw.Draw(sheet)
for i,r in enumerate(outliers):
 y=i*192;before=Image.open(root/'work/mods-upscale106-ui2/textures'/Path(r['replacement']).name).convert('RGBA');after=Image.open(root/r['replacement']).convert('RGBA');draw.text((4,y+3),f"{r['high_frequency_ratio']:.2f} | {r['id'][7:19]} | {(r['names'] or ['unnamed'])[0]}",fill='white')
 for offset,im in [(0,before),(512,after)]:
  scale=min(512/im.width,168/im.height);shown=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS);bg=Image.new('RGBA',(512,168),(75,75,75,255));bg.alpha_composite(shown,((512-shown.width)//2,(168-shown.height)//2));sheet.paste(bg.convert('RGB'),(offset,y+24))
outlier_path=root/'outputs/UPSCALER-107-environment-outliers.png';sheet.save(outlier_path);report['environment_outliers']=dict(file=outlier_path.relative_to(root).as_posix(),sha256=sha(outlier_path),ids=[r['id'] for r in outliers])
(root/'outputs/UPSCALER-107-raw-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
