"""Compare observed static strip vertices to unchanged converted section positions."""
import json,sys
from pathlib import Path
import numpy as np
r=Path(__file__).resolve().parent.parent
models={}
topologies={}
for p in (r/'work/world-analysis085').glob('section*.msh.json'):
 v=np.concatenate([np.array(s['vertices'])[:,:3] for s in json.loads(p.read_text())])
 models[p.name]=np.unique(v,axis=0)*np.array([-25/27,-25/27,25/27])
 q=models[p.name];indices={tuple(point):i for i,point in enumerate(q)}
 triangles=v.reshape(-1,3,3)*np.array([-25/27,-25/27,25/27])
 topologies[p.name]={tuple(sorted(indices[tuple(point)] for point in tri)) for tri in triangles}
report=[]
run=sys.argv[1] if len(sys.argv)>1 else 'coverage085-echo'
draws=[json.loads(l) for l in (r/'work/runs'/run/'world-draws.jsonl').read_text().splitlines()]
if run=='coverage086-echo':assert not any(d.get('sample_truncated') or d.get('truncated') for d in draws)
for i,d in enumerate(draws):
 if d['through'] or d['registered_model'] or len(d['samples'])<3:continue
 v=np.array(d['samples'])[:,:3];world=np.array(d['world']).reshape(4,3);v=v@world[:3]+world[3]
 best=[]
 for name,q in models.items():
  errors=np.min(np.max(np.abs(v[:,None,:]-q[None,:,:]),axis=2),axis=1)
  best.append(dict(model=name,matched=int(sum(errors<.003)),max_error=float(max(errors)),median_error=float(np.median(errors))))
 best.sort(key=lambda x:(-x['matched'],x['median_error']))
 report.append(dict(draw=i,primitive=d.get('primitive'),count=d.get('count'),world=d['world'],bounds=[v.min(0).tolist(),v.max(0).tolist()],best=best[:2]))
 # Source topology comparison distinguishes an absent vertex from changed triangulation.
 q=models[best[0]['model']]
 source_keys=topologies[best[0]['model']]
 distances=np.max(np.abs(v[:,None,:]-q[None,:,:]),axis=2)
 nearest=np.argmin(distances,axis=1)
 vertex_errors=distances[np.arange(len(v)),nearest]
 topology=[]
 for ti in range(2,len(v)):
  tri=v[ti-2:ti+1];area=np.linalg.norm(np.cross(tri[1]-tri[0],tri[2]-tri[0]))
  if area<1e-6:continue
  ids=nearest[ti-2:ti+1];errors=vertex_errors[ti-2:ti+1]
  topology.append(dict(triangle=ti-2,area=float(area),max_vertex_error=float(max(errors)),source_triangle=tuple(sorted(ids.tolist())) in source_keys,positions=tri.tolist() if max(errors)>=.003 else []))
 report[-1]['topology']=topology
(r/('outputs/ECHO-FULL-086.json' if run=='coverage086-echo' else 'outputs/ECHO-VERTEX-086.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps([dict(draw=x['draw'],matched_vertices=x['best'][0]['matched'],sample_triangles=len(x['topology']),exact_triangles=sum(t['source_triangle'] and t['max_vertex_error']<.003 for t in x['topology']),missing_vertices=sum(t['max_vertex_error']>=.003 for t in x['topology']),changed_topology=sum(not t['source_triangle'] and t['max_vertex_error']<.003 for t in x['topology'])) for x in report if x['best'][0]['matched']>=3],indent=2))
