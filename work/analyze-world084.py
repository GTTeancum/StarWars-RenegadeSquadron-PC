"""Compare observed world-space geometry to the user's unmodified MSH vertices."""
import collections, hashlib, json, os, subprocess
from pathlib import Path
import numpy as np
r=Path(__file__).resolve().parent.parent
run=r/'work/runs/coverage084-boz'
env=os.environ.copy();env['PATH']=str(r/'work/windows-sdk/bin')+os.pathsep+env['PATH']
audit=json.loads((r/'outputs/CONVERTED-BOZ-084.json').read_text())
out=r/'work/world-analysis084';out.mkdir(exist_ok=True)
models={}
for name,item in audit['models'].items():
    if not item['compiled']:continue
    path=out/(name+'.json')
    if not path.exists():
        data=subprocess.check_output([str(r/'work/build-windows-native/profiles/renegade/renegade_override_asset_audit.exe'),'--model-geometry',str(r/item['path'])],env=env)
        json.loads(data);path.write_bytes(data)
    segments=json.loads(path.read_text())
    vertices=np.concatenate([np.array(s['vertices'])[:,:3] for s in segments])
    vertices=np.unique(vertices,axis=0)
    models[name]=dict(vertices=vertices,bounds=[vertices.min(0).tolist(),vertices.max(0).tolist()],count=len(vertices))
if not (run/'world-draws.jsonl').exists():
    print(json.dumps({k:{q:v[q] for q in ['count','bounds']} for k,v in models.items()},indent=2));raise SystemExit(0)
draws=[json.loads(l) for l in (run/'world-draws.jsonl').read_text().splitlines()]
assert not any(d.get('truncated') for d in draws)
summary=collections.Counter()
groups={}
for d in draws:
    summary['draws']+=1;summary['through' if d['through'] else '3d']+=1
    if d['through']:continue
    key=(d.get('registered_model',''),tuple(d['world']),tuple(d['view']))
    g=groups.setdefault(key,dict(model=key[0],world=d['world'],view=d['view'],projection=d['projection'],draws=0,positions=[],vtypes=set(),textures=set()))
    g['draws']+=1;g['vtypes'].add(d['commands'][0x12]&0xffffff)
    g['textures'].add((d['commands'][0xa0]&0xffffff)|((d['commands'][0xa8]&0xf0000)<<8))
    g['positions'] += [s[:3] for s in d['samples'] if s is not None]
report=[]
for g in groups.values():
    positions=np.array(g.pop('positions'));g['vtypes']=sorted(g['vtypes']);g['textures']=sorted(g['textures'])
    if len(positions):
        world=np.array(g['world']).reshape(4,3)
        p=positions@world[:3,:]+world[3,:]
        g['raw_bounds']=[positions.min(0).tolist(),positions.max(0).tolist()]
        g['world_bounds']=[p.min(0).tolist(),p.max(0).tolist()]
        g['sample_world_positions']=p[:16].tolist()
    report.append(g)
result=dict(summary=dict(summary),groups=report,models={k:{q:v[q] for q in ['count','bounds']} for k,v in models.items()},trace_sha256=hashlib.sha256((run/'world-draws.jsonl').read_bytes()).hexdigest())
(r/'outputs/WORLD-DRAWS-084.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result['summary'],indent=2))

