"""Prepare independently verifiable RGB-only fidelity-upscaler examples."""
import hashlib,io,json,struct
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent.parent
catalog=json.loads((root/'work/texture-catalog105/catalog.json').read_text())
folder=root/'work/upscale106/pilot';inputs=folder/'input';outputs=folder/'neural'
inputs.mkdir(parents=True,exist_ok=True);outputs.mkdir(exist_ok=True)
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
chosen=[]
for token in ['brick','stone','wall','grass','snow','trooper','font','icon']:
 candidates=[r for r in catalog['images'] if r['base_image'] and not r['render_target_sample'] and
   not r['existing_pack_override'] and min(r['width'],r['height'])>=16 and
   any(token in n.lower() for n in r['names']) and r['id'] not in {x['id'] for x in chosen}]
 assert candidates,token
 r=candidates[0];p=root/r['original'];assert sha(p)==r['original_sha256']
 data=p.read_bytes();im=Image.open(io.BytesIO(data+bytes(max(0,26-len(data))))).convert('RGBA')
 assert 'tex-v1-'+hashlib.sha256(struct.pack('<II',*im.size)+im.tobytes()).hexdigest()==r['id']
 target=inputs/(r['id']+'.png')
 if not target.exists():im.convert('RGB').save(target)
 assert Image.open(target).convert('RGB').tobytes()==im.convert('RGB').tobytes()
 chosen.append(dict(token=token,id=r['id'],width=im.width,height=im.height,names=r['names'],original=r['original'],
   original_sha256=sha(p),input=target.relative_to(root).as_posix(),input_sha256=sha(target),alpha_policy='Source alpha kept separate, never neural-generated. Final pack policy chosen after pilot inspection.'))
tool=root/'work/upscale-tools/official-20220424/realesrgan-ncnn-vulkan.exe'
model=root/'work/upscale-tools/official-20210801/models'
cmd=[str(tool),'-i',str(inputs),'-o',str(outputs),'-m',str(model),'-n','realesrnet-x4plus','-s','4','-g','0','-t','512','-j','1:1:1','-f','png']
plan=dict(model='realesrnet-x4plus',source_catalog_sha256=sha(root/'work/texture-catalog105/catalog.json'),command=cmd,inputs=chosen,
 scope='Independent pilot only; no pack acceptance. No source transforms/channel swaps, face enhancement, GAN model, TTA, generated alpha or game mip/filter changes.')
p=root/'outputs/UPSCALER-106-pilot-plan.json'
if p.exists():assert json.loads(p.read_text())==plan
else:p.write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps(plan,indent=2))
