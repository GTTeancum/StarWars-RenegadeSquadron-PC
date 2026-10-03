"""Create explicit source/guest vertex bindings from verified full strip topology."""
import hashlib,json,subprocess,sys,os
from pathlib import Path
import numpy as np
r=Path(__file__).resolve().parent.parent
subprocess.run([sys.executable,str(r/'work/stage-echo085.py')],check=True)
old=r/'work/world-echo085.txt';lines=old.read_text().splitlines()
paths=[json.loads(x) for x in lines[1:]]
model_path=next(x for x in paths if Path(x).name.lower()=='sectiona.msh');model_index=paths.index(model_path)
geometry=json.loads((r/'work/world-analysis085/sectiona.msh.json').read_text())
env=os.environ.copy();env['PATH']=str(r/'work/windows-sdk/bin')+os.pathsep+env['PATH']
fresh=json.loads(subprocess.check_output([str(r/'work/build-windows-native/profiles/renegade/renegade_override_asset_audit.exe'),'--model-geometry',model_path],env=env))
assert fresh==geometry,'Saved source geometry differs from current compilation'
triangles=np.concatenate([np.array(s['vertices'])[:,:3] for s in geometry]).reshape(-1,3,3)*np.array([-25/27,-25/27,25/27])
points=np.unique(triangles.reshape(-1,3),axis=0);indices={tuple(p):i for i,p in enumerate(points)}
keys={tuple(sorted(indices[tuple(p)] for p in tri)) for tri in triangles}
draws=[json.loads(l) for l in (r/'work/runs/coverage086-echo/world-draws.jsonl').read_text().splitlines()]
bindings={};evidence=[]
for di in [145,146,147]:
 d=draws[di];assert not d['sample_truncated'] and d['primitive']>>16==4 and d['world']==[1,0,0,0,1,0,0,0,1,0,0,0]
 v=np.array(d['samples'])[:,:3];errors=np.max(np.abs(v[:,None,:]-points[None,:,:]),axis=2)
 nearest=np.argmin(errors,axis=1);distance=errors[np.arange(len(v)),nearest]
 assert max(distance)<1.5 and sum(distance<.003)/len(v)>.7
 tested=0
 for ti in range(2,len(v)):
  tri=v[ti-2:ti+1]
  if np.linalg.norm(np.cross(tri[1]-tri[0],tri[2]-tri[0]))<1e-6:continue
  assert tuple(sorted(nearest[ti-2:ti+1].tolist())) in keys
  tested+=1
 for vi in np.flatnonzero(distance>=.003):
  pi=int(nearest[vi]);ordered=np.sort(errors[vi]);assert ordered[1]-ordered[0]>.0001,'Ambiguous nearest authored vertex'
  if pi in bindings:assert max(abs(bindings[pi]-v[vi]))<.0001,'Conflicting guest positions'
  else:bindings[pi]=v[vi]
 evidence.append(dict(draw=di,vertices=len(v),verified_topology_triangles=tested,exact_vertices=int(sum(distance<.003)),max_delta=float(max(distance))))
lines[0]='RS_WORLD 3 '+' '.join(format(x,'.15g') for x in [-25/27,-25/27,25/27,0,0,0])+' '+str(len(paths))
lines.append('RS_BINDINGS '+str(len(bindings)))
entries=[]
for pi,guest in sorted(bindings.items()):
 source=points[pi];lines.append(str(model_index)+' '+' '.join(format(float(x),'.15g') for x in list(source)+list(guest)))
 entries.append(dict(model=model_index,source=source.tolist(),guest=guest.tolist()))
manifest=r/'work/world-echo087.txt';manifest.write_text('\n'.join(lines)+'\n')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
stage=json.loads((r/'outputs/WORLD-STAGE-085-PEB.json').read_text());stage.update(manifest=manifest.relative_to(r).as_posix(),manifest_sha256=sha(manifest),bindings=entries,evidence=evidence,trace_sha256=sha(r/'work/runs/coverage086-echo/world-draws.jsonl'),geometry_sha256=sha(r/'work/world-analysis085/sectiona.msh.json'),policy='Explicit model-specific source/guest vertex pairs; exact 0.003 triangle matching remains. Rendering positions, normals, pixels and UVs remain authored.')
(r/'outputs/WORLD-STAGE-087-PEB.json').write_text(json.dumps(stage,indent=2)+'\n')
print(json.dumps(dict(bindings=len(entries),evidence=evidence),indent=2))
