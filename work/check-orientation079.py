"""Analyze orientation correspondence without creating production replacements."""
import json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
r=Path(__file__).resolve().parent.parent
row=json.loads((r/'outputs/SOURCE-078-combined.json').read_text())[8]
g=row['game'];s=row['source'];a=Image.open(r/'work/texture-dumps058/textures'/(g['id']+'.png')).convert('RGBA');b=Image.open(r/s['paths'][0]).convert('RGBA')
assert hashlib.sha256((r/s['paths'][0]).read_bytes()).hexdigest()==s['file_sha256']
assert 'tex-v1-'+hashlib.sha256(a.width.to_bytes(4,'little')+a.height.to_bytes(4,'little')+a.tobytes()).hexdigest()==g['id']
ops=[('identity',None),('flip_horizontal',Image.Transpose.FLIP_LEFT_RIGHT),('flip_vertical',Image.Transpose.FLIP_TOP_BOTTOM),('rotate_180',Image.Transpose.ROTATE_180),('rotate_90',Image.Transpose.ROTATE_90),('rotate_270',Image.Transpose.ROTATE_270),('transpose',Image.Transpose.TRANSPOSE),('transverse',Image.Transpose.TRANSVERSE)]
results=[];sheet=Image.new('RGB',(1050,3*300),(35,35,35));d=ImageDraw.Draw(sheet)
a3=np.asarray(a.convert('RGB'),dtype=np.float32)
for i,(name,op) in enumerate(ops):
 t=b if op is None else b.transpose(op);arr=np.asarray(t.resize(a.size,Image.Resampling.BOX).convert('RGB'),dtype=np.float32)
 corr=float(np.corrcoef(a3.mean(2).ravel(),arr.mean(2).ravel())[0,1]);err=float(np.sqrt(np.mean((a3-arr)**2)));swap=float(np.sqrt(np.mean((a3[...,::-1]-arr)**2)))
 results.append(dict(operation=name,rgb_rmse=err,rgb_rmse_original_rb_swapped=swap,gray_correlation=corr))
 x=(i%3)*350;y=(i//3)*300;preview=t.convert('RGB');preview.thumbnail((256,256));sheet.paste(preview,(x,y+35));d.text((x,y),f'{name}: error {err:.2f} corr {corr:.3f}',fill='white')
sheet.save(r/'outputs/TEXTURE-ORIENTATION-079.png')
report=dict(original_id=g['id'],source=s,scope='Eight exact orientation transforms scored after BOX downsampling; diagnostic only, no production image change.',results=results)
(r/'outputs/TEXTURE-ORIENTATION-079.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(results,indent=2))
