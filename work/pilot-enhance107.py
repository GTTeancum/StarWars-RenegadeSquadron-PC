"""Run a stronger GAN pilot and prepare raw-texture comparisons for review."""
import hashlib, io, json, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

root=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
tool=root/'work/upscale-tools/official-20220424/realesrgan-ncnn-vulkan.exe'
models=root/'work/upscale-tools/official-20220424/models'
model_files=[models/'realesrgan-x4plus.bin',models/'realesrgan-x4plus.param']
pilot=json.loads((root/'outputs/UPSCALER-106-pilot-plan.json').read_text())['inputs']
selected=[r for r in pilot if r['token'] in {'brick','stone','wall','grass','snow','trooper'}]
work=root/'work/upscale107/pilot';inp=work/'input';gan=work/'gan'
inp.mkdir(parents=True,exist_ok=True);gan.mkdir(exist_ok=True)
rows=[]
for r in selected:
 source=root/r['original'];data=source.read_bytes();im=Image.open(io.BytesIO(data+bytes(max(0,26-len(data))))).convert('RGBA')
 target=inp/(r['id']+'.png')
 if not target.exists():im.convert('RGB').save(target)
 assert Image.open(target).convert('RGB').tobytes()==im.convert('RGB').tobytes()
 rows.append(dict(token=r['token'],id=r['id'],original=r['original'],original_sha256=sha(source),input=target.relative_to(root).as_posix(),input_sha256=sha(target),width=im.width,height=im.height))
command=[str(tool),'-i',str(inp),'-o',str(gan),'-m',str(models),'-n','realesrgan-x4plus','-s','4','-g','0','-t','512','-j','1:1:1','-f','png']
log=root/'outputs/UPSCALER-107-pilot-native.txt'
if not all((gan/(r['id']+'.png')).exists() for r in rows):
 result=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=600)
 log.write_text(result.stdout+result.stderr,encoding='utf-8');assert result.returncode==0
manifest=dict(model='realesrgan-x4plus',purpose='Visible world-texture enhancement pilot; UI excluded.',command=command,tool_sha256=sha(tool),model_sha256={p.name:sha(p) for p in model_files},inputs=rows)
(root/'outputs/UPSCALER-107-pilot-plan.json').write_text(json.dumps(manifest,indent=2)+'\n')
sheet=Image.new('RGB',(1024,384*len(rows)),(28,28,28));draw=ImageDraw.Draw(sheet)
review=[]
for index,r in enumerate(rows):
 original=Image.open(root/r['original']).convert('RGBA');size=(original.width*4,original.height*4)
 base=original.convert('RGB').resize(size,Image.Resampling.LANCZOS)
 nn=Image.open(gan/(r['id']+'.png')).convert('RGB');assert nn.size==size
 alpha=original.getchannel('A').resize(size,Image.Resampling.NEAREST)
 variants=[('source nearest',original.resize(size,Image.Resampling.NEAREST)),('checkpoint106',Image.open(root/'work/mods-upscale106-ui2/textures'/(r['id']+'.png')).convert('RGBA'))]
 a=np.asarray(base).astype(float);b=np.asarray(nn).astype(float)
 for label,weight in [('GAN 75%',.75),('GAN 100%',1.0)]:
  rgb=Image.fromarray(np.clip(np.rint(a*(1-weight)+b*weight),0,255).astype('uint8')).convert('RGBA');rgb.putalpha(alpha);variants.append((label,rgb))
 y=index*384;draw.text((4,y+4),r['token']+' | '+r['id'][7:23],fill='white')
 for column,(label,im) in enumerate(variants):
  x=column*256;draw.text((x+4,y+20),label,fill='white')
  scale=min(256/im.width,344/im.height);shown=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
  bg=Image.new('RGBA',(256,344),(75,75,75,255));bg.alpha_composite(shown,((256-shown.width)//2,(344-shown.height)//2));sheet.paste(bg.convert('RGB'),(x,y+40))
 review.append(dict(token=r['token'],id=r['id'],gan_sha256=sha(gan/(r['id']+'.png')),output_size=list(size),alpha_policy='Exact nearest-neighbor source alpha for candidates.'))
dest=root/'outputs/UPSCALER-107-pilot-comparison.png';sheet.save(dest)
(root/'outputs/UPSCALER-107-pilot-review.json').write_text(json.dumps(dict(sheet_sha256=sha(dest),samples=review,scope='Raw texture comparison only; select policy after visual review. No final pack or gameplay acceptance.'),indent=2)+'\n')
print(json.dumps(dict(samples=len(rows),sheet=dest.relative_to(root).as_posix(),model='realesrgan-x4plus'),indent=2))
