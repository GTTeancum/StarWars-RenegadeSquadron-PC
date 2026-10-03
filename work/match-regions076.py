"""Diagnostic atlas-region retrieval; never writes replacement assets."""
import hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
r=Path(__file__).resolve().parent.parent
rows=json.loads((r/'outputs/SOURCE-075-candidates.json').read_text());out=[]
for index in [0,5,6,11,14,28]:
 row=rows[index];identity=row['game']['id'];original=Image.open(r/'work/texture-dumps058/textures'/(identity+'.png')).convert('RGB');a=np.asarray(original.resize((64,64),Image.Resampling.BOX),dtype=np.float32)
 rgba=Image.open(r/'work/texture-dumps058/textures'/(identity+'.png')).convert('RGBA')
 assert 'tex-v1-'+hashlib.sha256(rgba.width.to_bytes(4,'little')+rgba.height.to_bytes(4,'little')+rgba.tobytes()).hexdigest()==identity
 probes=[]
 for y in range(0,64,16):
  for x in range(0,64,16):
   rgb=a[y:y+16,x:x+16];v=rgb.mean(2).ravel();v-=v.mean();norm=np.linalg.norm(v)
   if norm<80:continue
   probes.append(dict(x=x,y=y,v=v/norm,rgb=rgb,best=None))
 for candidate in row['candidates']:
  source=r/candidate['source']['paths'][0];assert hashlib.sha256(source.read_bytes()).hexdigest()==candidate['source']['file_sha256'];im=Image.open(source).convert('RGB')
  if min(im.size)<64:continue
  for side in [32,64,128]:
   dims=(side,max(16,round(side*im.height/im.width)));base=im.resize(dims,Image.Resampling.BOX)
   for rotation in range(4):
    b=np.rot90(np.asarray(base,dtype=np.float32),rotation);gray=b.mean(2)
    windows=np.lib.stride_tricks.sliding_window_view(gray,(16,16))[::2,::2];grid=windows.shape[:2];m=windows.reshape(-1,256).copy();m-=m.mean(1,keepdims=True);norm=np.linalg.norm(m,axis=1);m/=np.maximum(norm[:,None],1e-6)
    scores=np.stack([p['v'] for p in probes])@m.T
    for pi,p in enumerate(probes):
     k=int(np.argmax(scores[pi]));score=float(scores[pi,k]);sy,sx=np.unravel_index(k,grid);sx=int(sx)*2;sy=int(sy)*2
     if p['best'] is None or score>p['best']['correlation']:
      rgb=b[sy:sy+16,sx:sx+16];p['best']=dict(correlation=score,source=candidate['source']['paths'][0],source_sha256=candidate['source']['file_sha256'],resized_dimensions=dims,rotation_ccw_quarters=rotation,source_box_in_rotated_preview=[sx,sy,sx+16,sy+16],rgb_rmse=float(np.sqrt(np.mean((p['rgb']-rgb)**2))),rgb_rmse_original_rb_swapped=float(np.sqrt(np.mean((p['rgb'][...,::-1]-rgb)**2))))
 results=[dict(original_box_in_64px_preview=[p['x'],p['y'],p['x']+16,p['y']+16],**p['best']) for p in probes if p['best']]
 out.append(dict(row=index,id=identity,original_dimensions=original.size,regions=results))
 print(index,'regions',len(results),'correlation>=0.9',sum(v['correlation']>=.9 for v in results),flush=True)
report=dict(scope='Low-resolution region retrieval only. Gray correlation ignores color and cannot establish UV compatibility, region boundaries, improvement, or a safe replacement. Scale and rotation coordinates refer to analysis previews; no production assets modified.',results=out)
(r/'outputs/TEXTURE-REGIONS-076.json').write_text(json.dumps(report,indent=2)+'\n')
best=sorted([(g,v) for g in out for v in g['regions']],key=lambda p:p[1]['correlation'],reverse=True)[:24]
for start in range(0,len(best),8):
 sheet=Image.new('RGB',(850,8*138),(35,35,35));draw=ImageDraw.Draw(sheet)
 for j,(g,v) in enumerate(best[start:start+8]):
  a=Image.open(r/'work/texture-dumps058/textures'/(g['id']+'.png')).convert('RGB').resize((64,64),Image.Resampling.BOX).crop(v['original_box_in_64px_preview'])
  im=Image.open(r/v['source']).convert('RGB').resize(tuple(v['resized_dimensions']),Image.Resampling.BOX);b=Image.fromarray(np.rot90(np.asarray(im),v['rotation_ccw_quarters'])).crop(v['source_box_in_rotated_preview'])
  sheet.paste(a.resize((128,128),Image.Resampling.NEAREST),(0,j*138));sheet.paste(b.resize((128,128),Image.Resampling.NEAREST),(140,j*138));draw.text((280,j*138+8),f"row {g['row']} box {v['original_box_in_64px_preview']}\ncorrelation {v['correlation']:.3f} RGB error {v['rgb_rmse']:.1f}\n{Path(v['source']).name}",fill='white')
 sheet.save(r/f'outputs/TEXTURE-REGIONS-076-review-{start//8}.png')
