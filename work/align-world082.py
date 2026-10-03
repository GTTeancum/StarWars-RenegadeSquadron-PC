"""Measure coordinate correspondences; never rotate/flip any texture image."""
import itertools,json
from pathlib import Path
import numpy as np
r=Path(__file__).resolve().parent.parent
draws=[json.loads(l) for l in (r/'work/runs/coverage082-ordmantell/world-draws.jsonl').read_text().splitlines()]
original=[]
for d in draws:
    if d['through'] or d['registered_model'] or d['world'] != [1,0,0,0,1,0,0,0,1,0,0,0] or d['view'][9:]==[0,0,0]:continue
    original += [s[:3] for s in d['samples'] if s]
p=np.unique(np.round(np.array(original),3),axis=0)
sources=[]
for path in (r/'work/world-analysis082').glob('*.msh.json'):
    for s in json.loads(path.read_text()):sources+= [v[:3] for v in s['vertices']]
q=np.unique(np.round(np.array(sources),3),axis=0)
sample=p[::max(1,len(p)//200)]
results=[]
for signs in itertools.product([-1,1],repeat=3):
    transformed=q*np.array(signs)
    shifts=[]
    for axis in range(3):
        delta=np.round((sample[:,axis,None]-transformed[:,axis]).ravel(),2)
        values,counts=np.unique(delta,return_counts=True)
        order=np.argsort(counts)[-4:][::-1];shifts.append(values[order].tolist())
    source_set={tuple(v) for v in np.round(transformed,1)}
    best=[]
    for shift in itertools.product(*shifts):
        score=sum(tuple(v) in source_set for v in np.round(p-np.array(shift),1))
        best.append(dict(signs=signs,translation=shift,matches=score,samples=len(p)))
    results+=sorted(best,key=lambda x:-x['matches'])[:3]
results.sort(key=lambda x:-x['matches'])
(r/'outputs/WORLD-ALIGN-082.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results[:8],indent=2))
