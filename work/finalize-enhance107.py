"""Build the selected55percent ESRGAN detail pack after every chunk succeeds."""
import hashlib,json,shutil
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter
root=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
plan_path=root/'outputs/UPSCALER-107-plan.json';plan=json.loads(plan_path.read_text());state=json.loads((root/'work/upscale107/batch/run.json').read_text())
assert state['state']=='finished' and state['completed_images']==plan['images'] and state['completed_chunks']==plan['chunks'] and state['plan_sha256']==sha(plan_path)
receipts={}
for chunk in range(plan['chunks']):
 r=json.loads((root/f'work/upscale107/batch/{chunk:03d}/receipt.json').read_text());assert r['exit_code']==0;receipts.update(r['file_sha256'])
base_path=root/'outputs/TEXTURE-PACK-106-ui2.json';base=json.loads(base_path.read_text());targets={r['id']:r for r in plan['rows']}
folder=root/'work/mods-enhanced107/textures';folder.mkdir(parents=True,exist_ok=True);results=[]
def edge_energy(image):
 a=np.asarray(image.convert('L').filter(ImageFilter.FIND_EDGES),dtype=np.float32);return float(np.mean(np.abs(a[2:-2,2:-2]))) if min(a.shape)>4 else float(a.mean())
for index,r in enumerate(base['files']):
 prior=root/r['replacement'];assert sha(prior)==r['replacement_sha256'];dest=folder/prior.name;record=dict(r)
 if r['id'] in targets:
  t=targets[r['id']];assert sha(prior)==t['clean_sha256'];nn=root/t['neural'];assert sha(nn)==receipts[r['id']]
  clean=Image.open(prior).convert('RGBA');neural=Image.open(nn).convert('RGB');assert neural.size==clean.size==(t['width']*4,t['height']*4)
  assert np.any(np.asarray(neural)),'Reject corrupt all-black neural output'
  a=np.asarray(clean.convert('RGB'),dtype=float);b=np.asarray(neural,dtype=float);w=t['planned_weight'];rgb=Image.fromarray(np.clip(np.rint(a*(1-w)+b*w),0,255).astype('uint8')).convert('RGBA');rgb.putalpha(clean.getchannel('A'))
  if dest.exists():assert np.array_equal(np.asarray(Image.open(dest).convert('RGBA')),np.asarray(rgb))
  else:rgb.save(dest)
  original=Image.open(root/t['original']).convert('RGBA');expected=np.repeat(np.repeat(np.asarray(original)[:,:,3],4,0),4,1);assert np.array_equal(np.asarray(rgb)[:,:,3],expected)
  clean_energy=edge_energy(clean);final_energy=edge_energy(rgb)
  record.update(replacement=dest.relative_to(root).as_posix(),replacement_sha256=sha(dest),effective_method='esrgan_x4_detail55',detail_weight=w,neural_sha256=sha(nn),category=t['category'],clean_pack_sha256=t['clean_sha256'],high_frequency_energy_clean=clean_energy,high_frequency_energy_final=final_energy,high_frequency_ratio=final_energy/max(clean_energy,1e-6),alpha_exact_integer_replication=True)
 else:
  if dest.exists():assert dest.read_bytes()==prior.read_bytes()
  else:shutil.copyfile(prior,dest)
  side=prior.with_suffix('.json')
  if side.exists():
   target=dest.with_suffix('.json')
   if target.exists():assert target.read_bytes()==side.read_bytes()
   else:shutil.copyfile(side,target)
  record.update(replacement=dest.relative_to(root).as_posix(),replacement_sha256=sha(dest),checkpoint106_bytes_preserved=True)
 results.append(record)
 if (index+1)%256==0:print(f'Built {index+1}/{len(base["files"])}',flush=True)
report=dict(scale=4,parent_pack_sha256=sha(base_path),plan_sha256=sha(plan_path),batch_state_sha256=sha(root/'work/upscale107/batch/run.json'),policy=plan['policy'],enhanced_images=len(targets),preserved_images=len(results)-len(targets),category_counts=plan['category_counts'],files=results,excluded=base['excluded'],scope='All selected textures use exactly55percent ESRGAN detail over checkpoint106 clean RGB. Alpha, authored sources and exact/UI cases preserved. High-frequency metrics support ranked review; they do not prove every invented detail artistically correct. Gameplay acceptance pending.')
p=root/'outputs/TEXTURE-PACK-107.json'
if p.exists():assert json.loads(p.read_text())==report
else:p.write_text(json.dumps(report,indent=2)+'\n')
(folder.parent/'README.md').write_text('# Enhanced texture pack107\n\nUser-selected55% ESRGAN detail on1,827 eligible world textures over clean106. Existing355 authored replacements and exact UI/alpha cases remain unchanged. See outputs/TEXTURE-PACK-107.json. Replace by original content ID using DDS/TGA/PNG; keep one provider per ID.\n',encoding='utf-8')
print(json.dumps(dict(deployed=len(results),enhanced=len(targets),preserved=len(results)-len(targets),categories=plan['category_counts']),indent=2))
