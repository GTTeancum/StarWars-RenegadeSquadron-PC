"""Bind the additional fully verified translated Echo Base surface instance."""
import hashlib,json,subprocess,sys,statistics
from pathlib import Path
import numpy as np
r=Path(__file__).resolve().parent.parent
subprocess.run([sys.executable,str(r/'work/stage-echo087.py')],check=True)
alignment=json.loads((r/'outputs/WORLD-TRIANGLE-ALIGN-085.json').read_text())[3]
assert alignment['axes']==[0,1,2] and alignment['signs']==[-1,-1,1] and alignment['votes']==42
translation=np.array([statistics.median(x['fixed_scale_translation'][k] for x in alignment['precise']) for k in range(3)])
assert abs(translation[0]+2.94717767)<.0001 and max(abs(translation[1:]))<.0001
geometry=json.loads((r/'work/world-analysis088/sectiona.msh.json').read_text())
triangles=np.concatenate([np.array(s['vertices'])[:,:3] for s in geometry]).reshape(-1,3,3)*np.array([-25/27,-25/27,25/27])
points=np.unique(triangles.reshape(-1,3),axis=0);indices={tuple(p):i for i,p in enumerate(points)}
keys={tuple(sorted(indices[tuple(p)] for p in tri)) for tri in triangles}
draws=[json.loads(l) for l in (r/'work/runs/coverage086-echo/world-draws.jsonl').read_text().splitlines()]
bindings={};evidence=[]
for di in [168,169]:
 d=draws[di];assert not d['sample_truncated'] and d['primitive']>>16==4 and d['world']==[1,0,0,0,1,0,0,0,1,0,0,0]
 v=np.array(d['samples'])[:,:3];error=np.max(abs((v-translation)[:,None,:]-points[None,:,:]),axis=2)
 nearest=np.argmin(error,axis=1);dist=error[np.arange(len(v)),nearest];assert max(dist)<.0001
 tested=0
 for i in range(2,len(v)):
  tri=v[i-2:i+1]
  if np.linalg.norm(np.cross(tri[1]-tri[0],tri[2]-tri[0]))<1e-6:continue
  assert tuple(sorted(nearest[i-2:i+1].tolist())) in keys;tested+=1
 for vi,pi in enumerate(nearest.tolist()):
  if pi in bindings:assert max(abs(bindings[pi]-v[vi]))<.0001
  else:bindings[pi]=v[vi]
 evidence.append(dict(draw=di,vertices=len(v),verified_triangles=tested,max_residual=float(max(dist))))
manifest=r/'work/world-echo087.txt';lines=manifest.read_text().splitlines();count=int(lines[0].split()[-1]);binding_line=next(i for i,x in enumerate(lines) if x.startswith('RS_BINDINGS '))
paths=[json.loads(x) for x in lines[1:binding_line]];source=next(x for x in paths if Path(x).name.lower()=='sectiona.msh')
lines[0]=' '.join(lines[0].split()[:-1])+f' {count+1}';lines.insert(binding_line,json.dumps(source));binding_line+=1
old_count=int(lines[binding_line].split()[1]);lines[binding_line]=f'RS_BINDINGS {old_count+len(bindings)}'
for pi,guest in sorted(bindings.items()):lines.append(str(count)+' '+' '.join(format(float(x),'.15g') for x in list(points[pi])+list(guest)))
out=r/'work/world-echo088.txt';out.write_text('\n'.join(lines)+'\n');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
stage=json.loads((r/'outputs/WORLD-STAGE-087-PEB.json').read_text());stage.update(manifest=out.relative_to(r).as_posix(),manifest_sha256=sha(out),models=count+1,additional_instance=dict(model=source,coordinate_translation_evidence=translation.tolist(),bindings=len(bindings),draw_evidence=evidence),scope='Additional model-specific matching aliases preserve authored render geometry. Visible seams/collision differences remain subject to capture review; no all-map completion claim.')
(r/'outputs/WORLD-STAGE-088-PEB.json').write_text(json.dumps(stage,indent=2)+'\n')
print(json.dumps(stage['additional_instance'],indent=2))
