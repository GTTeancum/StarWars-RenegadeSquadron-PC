"""Plan a4x fallback pack from verified IDs, preserving authored replacements."""
import hashlib,io,json,re,struct
from pathlib import Path
from PIL import Image
import numpy as np
root=Path(__file__).resolve().parent.parent
catalog_path=root/'work/texture-catalog105/catalog.json';catalog=json.loads(catalog_path.read_text())
work=root/'work/upscale106/batch';work.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
source_pack=json.loads((root/'outputs/TEXTURE-PACK-074.json').read_text())
authored={r['id']:r for r in source_pack['files']};rows=[];excluded=[];neural=[]
for r in catalog['images']:
 if r['render_target_sample'] or r['status']=='runtime_zero_address':
  excluded.append(dict(id=r['id'],reason='captured mutable render-target frame, not a permanent authored asset' if r['render_target_sample'] else 'zero-address diagnostic sample'));continue
 p=root/r['original'];assert sha(p)==r['original_sha256'];data=p.read_bytes()
 im=Image.open(io.BytesIO(data+bytes(max(0,26-len(data))))).convert('RGBA')
 assert r['id']=='tex-v1-'+hashlib.sha256(struct.pack('<II',*im.size)+im.tobytes()).hexdigest()
 reasons=[]
 if r['id'] in authored:
  a=authored[r['id']];assert sha(root/a['replacement'])==a['sha256'];method='preferred_authored_source';reasons=['Existing verified source074 override; do not replace with upscaled PSP image.']
 else:
  paths=' '.join(r['names']+r['archives']).lower().replace('\\','/')
  if '/guimenu/' in '/'+paths or any(t in paths for t in ['/fonts/','/hud/','/interface/','/icons/','reticle','minimap','cursor','button','logo']):reasons.append('UI/text/symbol provenance: preserve exact source glyph and layout pixels.')
  if r['status'] in ['runtime_only_unresolved','exact_archive_rgb_alpha_variant']:reasons.append('Unresolved or alpha-variant provenance: conservative integer-scale fallback, no inferred art changes.')
  rgb=np.asarray(im)[:,:,:3]
  if min(im.size)<16:reasons.append('Tiny source; do not invent detail.')
  if np.unique(rgb.reshape(-1,3),axis=0).shape[0]<=8:reasons.append('Flat/limited palette source: preserve palette and geometric pixels exactly.')
  method='integer4x_preserve' if reasons else 'real_esrnet4x_fidelity_blend'
 row=dict(id=r['id'],width=im.width,height=im.height,original=r['original'],original_sha256=sha(p),names=r['names'],archives=r['archives'],status=r['status'],method=method,reasons=reasons)
 if method=='real_esrnet4x_fidelity_blend':
  chunk=len(neural)//64;folder=work/f'{chunk:03d}';inp=folder/'input';(folder/'neural').mkdir(parents=True,exist_ok=True);inp.mkdir(exist_ok=True)
  target=inp/(r['id']+'.png')
  if not target.exists():im.convert('RGB').save(target)
  assert Image.open(target).convert('RGB').tobytes()==im.convert('RGB').tobytes()
  row.update(chunk=chunk,input=target.relative_to(root).as_posix(),input_sha256=sha(target),neural=(folder/'neural'/(r['id']+'.png')).relative_to(root).as_posix())
  neural.append(row)
 rows.append(row)
plan=dict(scale=4,catalog_sha256=sha(catalog_path),source_pack_sha256=sha(root/'outputs/TEXTURE-PACK-074.json'),
 tool='work/upscale-tools/official-20220424/realesrgan-ncnn-vulkan.exe',model_folder='work/upscale-tools/official-20210801/models',model='realesrnet-x4plus',
 tool_sha256=sha(root/'work/upscale-tools/official-20220424/realesrgan-ncnn-vulkan.exe'),
 model_sha256={p.name:sha(p) for p in (root/'work/upscale-tools/official-20210801/models').glob('realesrnet-x4plus.*')},
 rows=rows,excluded=excluded,counts={m:sum(r['method']==m for r in rows) for m in sorted({r['method'] for r in rows})},
 neural_images=len(neural),chunks=(len(neural)+63)//64,
 policy='4x exact dimensions. Source channels/orientation unchanged. Alpha exactly integer-replicated; never neural-generated. Neural RGB mixed at most50percent with Lanczos reference, further limited by source downsample drift. UI/unknown/tiny/limited-palette inputs retain exact integer-replicated RGBA. Existing355 source overrides remain byte-identical/preferred. Dynamic RT/zero samples retained as originals, explicitly not deployed. No mip/filter changes, inferred source matches, model bindings, TTA, faces or GAN enhancement.')
p=root/'outputs/UPSCALER-106-plan.json'
if p.exists():assert json.loads(p.read_text())==plan
else:p.write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({k:v for k,v in plan.items() if k not in ['rows','excluded']},indent=2))
