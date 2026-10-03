"""Prepare a visible-detail ESRGAN layer for non-UI, non-authored world textures."""
import hashlib, io, json
from collections import Counter
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
source_path=root/'outputs/TEXTURE-PACK-106-ui2.json';source=json.loads(source_path.read_text())
work=root/'work/upscale107/batch';work.mkdir(parents=True,exist_ok=True)
rows=[]
for r in source['files']:
 effective=r.get('effective_method',r['method'])
 if effective!='real_esrnet4x_fidelity_blend':continue
 names=[v.lower().replace('\\','/') for v in r['names']]
 joined=' '.join(names)
 if any(t in joined for t in ['/characters/','/weapons/','/vehicles/','trooper','soldier','droid','face','body','helmet']):category='character_vehicle_weapon'
 elif any(t in joined for t in ['/effects/','/particles/','/sky/','foliage','vegetation','grass','tree','plant','cloud','smoke','fire','beam']):category='effect_foliage_sky'
 elif any(t in joined for t in ['/environments/','/terrain/','/objects/','wall','floor','rock','stone','metal','building','ground','snow']):category='environment_surface'
 else:category='general_world'
 weight=.55
 original=root/r['original'];assert sha(original)==r['original_sha256']
 data=original.read_bytes();im=Image.open(io.BytesIO(data+bytes(max(0,26-len(data))))).convert('RGBA')
 chunk=len(rows)//64;folder=work/f'{chunk:03d}';inp=folder/'input';(folder/'neural').mkdir(parents=True,exist_ok=True);inp.mkdir(exist_ok=True)
 target=inp/(r['id']+'.png')
 if not target.exists():im.convert('RGB').save(target)
 assert Image.open(target).convert('RGB').tobytes()==im.convert('RGB').tobytes()
 rows.append(dict(id=r['id'],width=im.width,height=im.height,original=r['original'],original_sha256=r['original_sha256'],clean=r['replacement'],clean_sha256=r['replacement_sha256'],names=r['names'],archives=r['archives'],category=category,planned_weight=weight,chunk=chunk,input=target.relative_to(root).as_posix(),input_sha256=sha(target),neural=(folder/'neural'/(r['id']+'.png')).relative_to(root).as_posix()))
tool=root/'work/upscale-tools/official-20220424/realesrgan-ncnn-vulkan.exe';models=root/'work/upscale-tools/official-20210801/models'
plan=dict(scale=4,source_pack_sha256=sha(source_path),tool='work/upscale-tools/official-20220424/realesrgan-ncnn-vulkan.exe',model_folder='work/upscale-tools/official-20210801/models',model='esrgan-x4',tool_sha256=sha(tool),model_sha256={p.name:sha(p) for p in models.glob('esrgan-x4.*')},rows=rows,images=len(rows),chunks=(len(rows)+63)//64,category_counts=dict(Counter(r['category'] for r in rows)),policy='User-selected55percent ESRGAN detail layer over checkpoint106 clean output for every eligible non-UI texture. Existing355 authored replacements and all exact/UI cases remain byte-identical. Alpha/channel/orientation unchanged; no mip/filter changes. Reject corrupt/dimension/alpha failures; do not silently reduce the selected detail strength.')
p=root/'outputs/UPSCALER-107-plan.json';assert not (work/'run.json').exists(),'Plan is immutable after batch start';p.write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({k:v for k,v in plan.items() if k!='rows'},indent=2))
