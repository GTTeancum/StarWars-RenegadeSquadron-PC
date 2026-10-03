"""Estimate map coordinate mapping from matching triangle shapes, not textures."""
import collections,itertools,json
from pathlib import Path
import numpy as np
r=Path(__file__).resolve().parent.parent
draws=[json.loads(l) for l in (r/'work/runs/coverage084-boz/world-draws.jsonl').read_text().splitlines()]
def signature(v):
    lengths=np.sort(np.linalg.norm(v-np.roll(v,1,axis=0),axis=1))
    if lengths[0]<.01:return None
    return tuple(np.round(lengths[:2]/lengths[2],3)),lengths[2]
source=collections.defaultdict(list)
for path in (r/'work/world-analysis084').glob('*.msh.json'):
    for seg in json.loads(path.read_text()):
        v=np.array(seg['vertices'])[:,:3].reshape(-1,3,3)
        for tri in v:
            s=signature(tri)
            if s:source[s[0]].append((path.name,tri,s[1]))
votes=collections.Counter();examples={};precise=collections.defaultdict(list)
perms=list(itertools.permutations(range(3)));signs=list(itertools.product([-1,1],repeat=3))
variants=[(axes,sign,order) for axes in perms for sign in signs for order in perms]
axes_array=np.array([x[0] for x in variants]);sign_array=np.array([x[1] for x in variants]);order_array=np.array([x[2] for x in variants])
for di,d in enumerate(draws):
    if d['through'] or d['registered_model'] or d['world'] != [1,0,0,0,1,0,0,0,1,0,0,0] or d['view'][9:]==[0,0,0]:continue
    p=np.array(d['samples'])[:,:3]
    for i in range(len(p)-2):
        tri=p[i:i+3];s=signature(tri)
        if not s:continue
        candidates=source.get(s[0],[])
        if len(candidates)>50:continue
        for name,q,ql in candidates:
            scale=s[1]/ql
            if not .05<scale<20:continue
            # Test axis conventions and vertex order; no image operations.
            aligned=q[order_array[:,:,None],axes_array[:,None,:]]*sign_array[:,None,:]*scale
            shift=(tri-aligned).mean(1)
            errors=np.max(np.abs(tri-aligned-shift[:,None,:]),axis=(1,2))
            for vi in np.flatnonzero(errors<.015):
                axes,sign,order=variants[vi]
                key=(axes,sign,round(scale,3),tuple(np.round(shift[vi],2)))
                votes[key]+=1;examples[key]=dict(draw=di,model=name,error=float(errors[vi]));precise[key].append(dict(scale=float(scale),translation=shift[vi].tolist(),fixed_scale_translation=(tri-aligned[vi]/scale*(5/6)).mean(0).tolist(),model=name))
result=[dict(axes=k[0],signs=k[1],scale=k[2],translation=k[3],votes=n,example=examples[k],precise=precise[k]) for k,n in votes.most_common(20)]
(r/'outputs/WORLD-TRIANGLE-ALIGN-084.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps([{k:v for k,v in x.items() if k!='precise'} for x in result[:5]],indent=2))

