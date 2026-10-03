"""Independently recompute every blend and preservation claim in pack107."""
import hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parent.parent;sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
plan_path=root/'outputs/UPSCALER-107-plan.json';pack_path=root/'outputs/TEXTURE-PACK-107.json';plan=json.loads(plan_path.read_text());pack=json.loads(pack_path.read_text())
base=json.loads((root/'outputs/TEXTURE-PACK-106-ui2.json').read_text());base_rows={r['id']:r for r in base['files']};targets={r['id']:r for r in plan['rows']};rows={r['id']:r for r in pack['files']}
assert len(rows)==len(base_rows)==2568 and sha(plan_path)==pack['plan_sha256'] and sha(root/'outputs/TEXTURE-PACK-106-ui2.json')==pack['parent_pack_sha256']
artifacts={pack_path.relative_to(root).as_posix():sha(pack_path)}
for id_,r in rows.items():
 p=root/r['replacement'];assert sha(p)==r['replacement_sha256'];providers=[p.with_suffix(e) for e in ['.dds','.tga','.png'] if p.with_suffix(e).exists()];assert providers==[p]
 prior=root/base_rows[id_]['replacement'];assert sha(prior)==base_rows[id_]['replacement_sha256']
 if id_ in targets:
  t=targets[id_];assert r['detail_weight']==.55 and r['effective_method']=='esrgan_x4_detail55'
  clean=Image.open(prior).convert('RGBA');nn=Image.open(root/t['neural']).convert('RGB');final=Image.open(p).convert('RGBA')
  w=r['detail_weight'];expected=np.clip(np.rint(np.asarray(clean.convert('RGB'),dtype=float)*(1-w)+np.asarray(nn,dtype=float)*w),0,255).astype('uint8')
  assert np.array_equal(np.asarray(final)[:,:,:3],expected),id_
  assert np.array_equal(np.asarray(final)[:,:,3],np.asarray(clean)[:,:,3]),id_
  assert sha(root/t['neural'])==r['neural_sha256']
 else:
  assert p.read_bytes()==prior.read_bytes() and r['checkpoint106_bytes_preserved']
  side=prior.with_suffix('.json')
  if side.exists():assert p.with_suffix('.json').read_bytes()==side.read_bytes()
 artifacts[p.relative_to(root).as_posix()]=sha(p)
receipt=dict(deployed_images=len(rows),enhanced_images=len(targets),preserved_checkpoint106_images=len(rows)-len(targets),authored_preserved=sum(r['method']=='preferred_authored_source' for r in rows.values()),exact_weight=.55,artifact_sha256=artifacts,scope='Every output hash/provider, exact55percent RGB blend, neural hash, source alpha and unchanged checkpoint106 file/sidecar verified. Artistic review and gameplay are separate.')
p=root/'outputs/UPSCALER-107-verification.json'
if p.exists():assert json.loads(p.read_text())==receipt
else:p.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='artifact_sha256'},indent=2))
