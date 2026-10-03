"""Construct and verify final fallback images from immutable native intermediates."""
import hashlib,io,json,struct
from collections import Counter
from pathlib import Path
from PIL import Image
import numpy as np
root=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
plan_path=root/'outputs/UPSCALER-106-plan.json';plan=json.loads(plan_path.read_text())
state=json.loads((root/'work/upscale106/batch/run.json').read_text())
assert state['state']=='finished' and state['completed_images']==plan['neural_images'] and state['completed_chunks']==plan['chunks']
assert sha(plan_path)==state['plan_sha256']
folder=root/'work/mods-upscale106/textures';folder.mkdir(parents=True,exist_ok=True)
source=json.loads((root/'outputs/TEXTURE-PACK-074.json').read_text());authored={r['id']:r for r in source['files']}
receipts={}
for chunk in range(plan['chunks']):
 p=root/f'work/upscale106/batch/{chunk:03d}/receipt.json';r=json.loads(p.read_text());assert r['exit_code']==0
 receipts.update(r['file_sha256'])
results=[]
def atomic_image(image,path):
 if path.exists():assert Image.open(path).convert('RGBA').tobytes()==image.convert('RGBA').tobytes();return
 tmp=path.with_suffix('.next');image.save(tmp,format='PNG');tmp.replace(path)
for row in plan['rows']:
 original=root/row['original'];assert sha(original)==row['original_sha256']
 data=original.read_bytes();im=Image.open(io.BytesIO(data+bytes(max(0,26-len(data))))).convert('RGBA')
 assert 'tex-v1-'+hashlib.sha256(struct.pack('<II',*im.size)+im.tobytes()).hexdigest()==row['id']
 src=np.asarray(im);record={k:row[k] for k in ['id','original','original_sha256','width','height','names','archives','status','method','reasons']}
 if row['method']=='preferred_authored_source':
  a=authored[row['id']];p=root/a['replacement'];assert sha(p)==a['sha256'];dest=folder/p.name
  if dest.exists():assert dest.read_bytes()==p.read_bytes()
  else:dest.write_bytes(p.read_bytes())
  side=p.with_suffix('.json')
  if side.exists():
   target=folder/side.name
   if target.exists():assert target.read_bytes()==side.read_bytes()
   else:target.write_bytes(side.read_bytes())
  record.update(replacement=dest.relative_to(root).as_posix(),replacement_sha256=sha(dest),preferred_source_preserved=True,output_size=Image.open(dest).size)
 else:
  size=(im.width*4,im.height*4);weight=0.0
  if row['method']=='integer4x_preserve' or not np.any(src[:,:,3]):
   final=im.resize(size,Image.Resampling.NEAREST);metrics=dict(rgb_mae=0.0,rgb_p99=0.0,max_channel_error=0,mean_channel_shift=[0.,0.,0.])
   if row['method']!='integer4x_preserve':record['effective_method']='integer4x_preserve_fully_transparent_source'
  else:
   p=root/row['neural'];assert sha(p)==receipts[row['id']]
   nn=Image.open(p).convert('RGB');assert nn.size==size
   native_black=not np.any(np.asarray(nn))
   base=im.convert('RGB').resize(size,Image.Resampling.LANCZOS)
   small=np.asarray(nn.resize(im.size,Image.Resampling.BOX)).astype(float);visible=src[:,:,3]>0
   delta=(small-src[:,:,:3])[visible];mae=float(np.abs(delta).mean());p99=float(np.percentile(np.abs(delta),99));shift=np.mean(delta,axis=0)
   weight=min(.5,4/max(mae,1e-6),20/max(p99,1e-6),2/max(float(np.abs(shift).max()),1e-6))
   if native_black:
    weight=0;record['effective_method']='lanczos4x_native_black_rejection'
    record['neural_rejection']='Unexpected all-black native result; do not mix it into the asset.'
   # Reject excessive alteration instead of claiming every neural result faithful.
   a=np.asarray(base).astype(float);b=np.asarray(nn).astype(float)
   for attempt in range(8):
    rgb=Image.fromarray(np.clip(np.rint(a*(1-weight)+b*weight),0,255).astype('uint8'))
    reduced=np.asarray(rgb.resize(im.size,Image.Resampling.BOX)).astype(float)
    d=(reduced-src[:,:,:3])[visible];metrics=dict(rgb_mae=float(np.abs(d).mean()),rgb_p99=float(np.percentile(np.abs(d),99)),max_channel_error=int(np.abs(d).max()),mean_channel_shift=[float(v) for v in np.mean(d,axis=0)])
    if metrics['rgb_mae']<=8 and metrics['rgb_p99']<=40 and max(abs(v) for v in metrics['mean_channel_shift'])<=3:break
    weight=weight*.5 if attempt<6 else 0
   else:
    rgb=im.convert('RGB').resize(size,Image.Resampling.NEAREST);weight=0
    metrics=dict(rgb_mae=0.0,rgb_p99=0.0,max_channel_error=0,mean_channel_shift=[0.,0.,0.])
    record['effective_method']='integer4x_fidelity_rejection'
    record['fidelity_rejection']='Neither neural blend nor Lanczos reference meets source-consistency bounds; preserve exact source pixels instead.'
   final=rgb.convert('RGBA');final.putalpha(im.getchannel('A').resize(size,Image.Resampling.NEAREST))
   record.update(neural_sha256=sha(p),neural_native_rgb_mae=mae,neural_native_rgb_p99=p99,neural_weight=weight,
    fidelity_scope='Source-sized BOX reconstruction metrics on visible pixels; automated evidence, not proof of every fine feature. NN limited at most50percent, with original Lanczos reference retained.')
  expected_alpha=np.repeat(np.repeat(src[:,:,3],4,axis=0),4,axis=1)
  assert final.size==size and np.array_equal(np.asarray(final)[:,:,3],expected_alpha)
  if row['method']=='integer4x_preserve':assert np.array_equal(np.asarray(final),np.repeat(np.repeat(src,4,axis=0),4,axis=1))
  dest=folder/(row['id']+'.png');atomic_image(final,dest)
  record.update(replacement=dest.relative_to(root).as_posix(),replacement_sha256=sha(dest),output_size=size,alpha_exact_integer_replication=True,source_fidelity=metrics)
 results.append(record)
 if len(results)%128==0:print(f'Final images verified {len(results)}/{len(plan["rows"])}',flush=True)
report=dict(scale=4,plan_sha256=sha(plan_path),native_run_sha256=sha(root/'work/upscale106/batch/run.json'),policy=plan['policy'],counts=plan['counts'],effective_counts=dict(Counter(r.get('effective_method',r['method']) for r in results)),files=results,excluded=plan['excluded'],
 visual_scope='Representative pilot inspected; source consistency/dimensions/alpha verified for every generated image. Representative in-game replacement/precedence checks still required. No every-asset artistic certification. Existing source replacements preserved at authored dimensions, not forced through PSP upscaling.')
p=root/'outputs/TEXTURE-PACK-106.json'
if p.exists():assert json.loads(p.read_text())==report
else:p.write_text(json.dumps(report,indent=2)+'\n')
(root/'work/mods-upscale106/README.md').write_text('# Fidelity4x fallback pack\n\n'+plan['policy']+'\n\nReplace an ID image in textures/ with your authored DDS/TGA/PNG. Keep only one image extension per ID to avoid loader precedence ambiguity. Use the original decoded content ID as the filename, never the hash of the upscaled pixels. Existing355 source images are preferred and unchanged; other generated replacements are4x. See outputs/TEXTURE-PACK-106.json for per-image provenance and drift metrics.\n',encoding='utf-8')
print(json.dumps({'deployed_images':len(results),'methods':plan['counts'],'excluded_dynamic_or_zero':len(plan['excluded'])},indent=2))
