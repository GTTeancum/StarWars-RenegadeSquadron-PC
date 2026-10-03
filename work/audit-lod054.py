"""Audit observed LOD replacement draws without treating loads as draws."""
import hashlib,json,re
from pathlib import Path
root=Path(__file__).resolve().parent.parent;run=root/'work/runs/lod054-movement'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
meta=json.loads((run/'run.json').read_text());assert meta['state']=='finished' and meta['exit_code']==0 and not meta['timed_out']
assert any('VBlank diagnostic stop at 2876' in s for s in meta['stop_lines'])
log=(run/'native.log').read_text(errors='replace');assert 'Skin deformation failed' not in log
rows=[json.loads(s) for s in (run/'resources.jsonl').read_text().splitlines()]
names=['battle_droid','L1#battle_droid','L2#battle_droid'];result={}
for name in names:
    draws=[]
    for s in log.splitlines():
        if 'Skinned MSH draw ' in s and ('models\\'+name+'\\model.msh') in s:
            draws.append({k:int(re.search(r'\b'+k+r'=(\d+)',s)[1]) for k in ['submitted','prepared','pixels_written']})
    result[name]={'resource_loads':[r for r in rows if r.get('event')=='load' and r.get('name')==name],
                  'original_draw_samples':sum(r.get('event')=='draw' and r.get('name')==name for r in rows),
                  'replacement_draw_samples':draws}
assert all(result[n]['resource_loads'] for n in names)
assert all(any(d['pixels_written']>0 for d in result[n]['replacement_draw_samples']) for n in names)
frames=sorted((run/'frames').glob('*.ppm'));assert len(frames)==7
paths=[Path(__file__),run/'run.json',run/'native.log',run/'resources.jsonl',root/'work/skin043-movement-replay.txt']+frames+list((root/'work/mods-skin053-lods').rglob('*'))
report={'scope':'Observed positive-pixel replacement draws for base, L1 and L2; same-actor transition continuity is not certified','native_run':meta,'variants':result,'sha256':{p.relative_to(root).as_posix():sha(p) for p in paths if p.is_file()}}
(root/'outputs/LOD-054-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({n:{'loads':len(v['resource_loads']),'original_draws':v['original_draw_samples'],'replacement_draws':len(v['replacement_draw_samples'])} for n,v in result.items()},indent=2))
