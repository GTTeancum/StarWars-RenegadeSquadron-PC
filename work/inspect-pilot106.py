"""Measure source fidelity, preserve alpha and make an internal comparison sheet."""
import hashlib,io,json
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np
root=Path(__file__).resolve().parent.parent
plan=json.loads((root/'outputs/UPSCALER-106-pilot-plan.json').read_text())
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
reports=[];sheet=Image.new('RGB',(1024,600*len(plan['inputs'])),(24,28,32));draw=ImageDraw.Draw(sheet)
for i,row in enumerate(plan['inputs']):
 source=root/row['original'];assert sha(source)==row['original_sha256']
 data=source.read_bytes();original=Image.open(io.BytesIO(data+bytes(max(0,26-len(data))))).convert('RGBA')
 target=root/'work/upscale106/pilot/neural'/(row['id']+'.png');neural=Image.open(target).convert('RGB')
 assert neural.size==(original.width*4,original.height*4)
 small=np.asarray(neural.resize(original.size,Image.Resampling.BOX)).astype(float)
 src=np.asarray(original).astype(float);visible=src[:,:,3]>0
 delta=np.abs(small-src[:,:,:3]);values=delta[visible]
 assert len(values)>0 and np.any(np.asarray(neural)!=0)
 alpha=original.getchannel('A').resize(neural.size,Image.Resampling.NEAREST)
 rgba=neural.convert('RGBA');rgba.putalpha(alpha)
 final=root/'work/upscale106/pilot'/(row['id']+'-alpha-preserved.png');rgba.save(final)
 assert np.array_equal(np.asarray(rgba)[:,:,3],np.repeat(np.repeat(src[:,:,3].astype('uint8'),4,axis=0),4,axis=1))
 reports.append(dict(id=row['id'],token=row['token'],source_size=original.size,result_size=neural.size,
  visible_rgb_mae=float(values.mean()),visible_rgb_p99=float(np.percentile(values,99)),visible_rgb_max=float(values.max()),
  mean_channel_shift=[float(np.mean((small-src[:,:,:3])[visible][:,c])) for c in range(3)],
  neural_sha256=sha(target),alpha_exact_integer_replication=True,composite_sha256=sha(final)))
 # QA-only scale to fit512px cards; these are explicitly not game captures.
 baseline=original.convert('RGB').resize(neural.size,Image.Resampling.NEAREST)
 for x,image in [(0,baseline),(512,neural)]:
  image.thumbnail((512,550),Image.Resampling.NEAREST);sheet.paste(image,(x,i*600+35))
 draw.text((8,i*600+7),row['token']+' — source integer-scale reference',fill='white')
 draw.text((520,i*600+7),'RealESRNet4x, RGB only; alpha verified separately',fill='white')
sheet.save(root/'outputs/UPSCALER-106-pilot-comparison.png')
p=root/'outputs/UPSCALER-106-pilot-review.json';assert not p.exists();p.write_text(json.dumps(reports,indent=2)+'\n')
print(json.dumps(reports,indent=2))
