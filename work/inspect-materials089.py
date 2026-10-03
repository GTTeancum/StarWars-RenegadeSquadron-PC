"""Inspect authored material images and relate full draw triangles to source slots."""
import hashlib,json,collections
from pathlib import Path
import numpy as np
from PIL import Image
r=Path(__file__).resolve().parent.parent
base=r/'work/map-conversions085/data_PEB/Worlds/PEB/msh'
out=r/'outputs/material-inspection089';out.mkdir(exist_ok=True)
images=[]
for name in ['PSP_0006_0.tga','PSP_0008_0.tga','hoth_main_1.tga','hoth_tunnels_02.tga','hoth_frosty_metals.tga']:
 p=base/name;im=Image.open(p);dest=out/(p.stem+'.png');im.save(dest)
 images.append(dict(source=p.relative_to(r).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),dimensions=list(im.size),preview=dest.relative_to(r).as_posix()))
geometries=json.loads((r/'work/world-analysis088/sectiona.msh.json').read_text())
q=np.concatenate([np.array(s['vertices'])[:,:3] for s in geometries])*np.array([-25/27,-25/27,25/27]);points=np.unique(q,axis=0)
indices={tuple(p):i for i,p in enumerate(points)};materials=collections.defaultdict(set)
for s in geometries:
 for tri in np.array(s['vertices'])[:,:3].reshape(-1,3,3)*np.array([-25/27,-25/27,25/27]):
  materials[tuple(sorted(indices[tuple(p)] for p in tri))].add(s['texture'])
draws=[json.loads(l) for l in (r/'work/runs/coverage086-echo/world-draws.jsonl').read_text().splitlines()]
report=[]
for di in [124,125,135,140,144,145,146,147,168,169,178]:
 d=draws[di];v=np.array(d['samples'])[:,:3]
 if di in [168,169]:v=v-np.array([-2.9471776716049383,3.1770802468855663e-5,1.2098765533134308e-6])
 error=np.max(abs(v[:,None,:]-points[None,:,:]),axis=2);nearest=np.argmin(error,axis=1);counts=collections.Counter()
 for i in range(2,len(v)):
  tri=v[i-2:i+1]
  if np.linalg.norm(np.cross(tri[1]-tri[0],tri[2]-tri[0]))<1e-6:continue
  key=tuple(sorted(nearest[i-2:i+1].tolist()));counts.update(materials.get(key,{'unmatched'}))
 report.append(dict(draw=di,source_material_triangles=dict(counts)))
(r/'outputs/MATERIAL-089-inspection.json').write_text(json.dumps(dict(images=images,draw_materials=report),indent=2)+'\n')
print(json.dumps(report,indent=2))
