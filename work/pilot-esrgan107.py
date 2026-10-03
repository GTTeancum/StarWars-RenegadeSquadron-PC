"""Compare sharper ESRGAN output against the rejected conservative pack and RealESRGAN."""
import hashlib, io, json, subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
tool=root/'work/upscale-tools/official-20220424/realesrgan-ncnn-vulkan.exe';models=root/'work/upscale-tools/official-20210801/models'
plan=json.loads((root/'outputs/UPSCALER-107-pilot-plan.json').read_text());rows=plan['inputs']
inp=root/'work/upscale107/pilot/input';out=root/'work/upscale107/pilot/esrgan';out.mkdir(exist_ok=True)
cmd=[str(tool),'-i',str(inp),'-o',str(out),'-m',str(models),'-n','esrgan-x4','-s','4','-g','0','-t','512','-j','1:1:1','-f','png']
log=root/'outputs/UPSCALER-107-esrgan-pilot-native.txt'
if not all((out/(r['id']+'.png')).exists() for r in rows):
 result=subprocess.run(cmd,cwd=root,capture_output=True,text=True,timeout=600);log.write_text(result.stdout+result.stderr,encoding='utf-8');assert result.returncode==0
sheet=Image.new('RGB',(1024,384*len(rows)),(28,28,28));draw=ImageDraw.Draw(sheet);samples=[]
for index,r in enumerate(rows):
 data=(root/r['original']).read_bytes();original=Image.open(io.BytesIO(data+bytes(max(0,26-len(data))))).convert('RGBA');size=(original.width*4,original.height*4)
 alpha=original.getchannel('A').resize(size,Image.Resampling.NEAREST);base=original.convert('RGB').resize(size,Image.Resampling.LANCZOS)
 current=Image.open(root/'work/mods-upscale106-ui2/textures'/(r['id']+'.png')).convert('RGBA')
 real=Image.open(root/'work/upscale107/pilot/gan'/(r['id']+'.png')).convert('RGB');esr=Image.open(out/(r['id']+'.png')).convert('RGB')
 def blend(nn,weight):
  a=np.asarray(base).astype(float);b=np.asarray(nn).astype(float);im=Image.fromarray(np.clip(np.rint(a*(1-weight)+b*weight),0,255).astype('uint8')).convert('RGBA');im.putalpha(alpha);return im
 variants=[('source nearest',original.resize(size,Image.Resampling.NEAREST)),('checkpoint106',current),('RealESRGAN100',blend(real,1)),('ESRGAN100',blend(esr,1))]
 y=index*384;draw.text((4,y+4),r['token']+' | '+r['id'][7:23],fill='white')
 for col,(label,im) in enumerate(variants):
  x=col*256;draw.text((x+4,y+20),label,fill='white');scale=min(256/im.width,344/im.height);shown=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
  bg=Image.new('RGBA',(256,344),(75,75,75,255));bg.alpha_composite(shown,((256-shown.width)//2,(344-shown.height)//2));sheet.paste(bg.convert('RGB'),(x,y+40))
 samples.append(dict(token=r['token'],id=r['id'],esrgan_sha256=sha(out/(r['id']+'.png')),output_size=list(size)))
dest=root/'outputs/UPSCALER-107-model-comparison.png';sheet.save(dest)
receipt=dict(command=cmd,tool_sha256=sha(tool),model_sha256={p.name:sha(p) for p in models.glob('esrgan-x4.*')},sheet_sha256=sha(dest),samples=samples,scope='Raw texture model comparison. No final policy/gameplay acceptance.')
(root/'outputs/UPSCALER-107-model-comparison.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(samples=len(samples),sheet=dest.relative_to(root).as_posix()),indent=2))
