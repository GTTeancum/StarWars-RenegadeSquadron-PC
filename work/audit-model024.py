"""Verify subtype-5 archive layout and correlate observed GE draws to model parts."""
from pathlib import Path
import collections
import hashlib
import json
import struct

root=Path(__file__).resolve().parent
catalog=json.loads((root.parent/'outputs/ASURA-023-catalog.json').read_text())
strides=collections.Counter()
checked=0
for archive in catalog['archives']:
    data=(root/'game/disc'/archive['file']).read_bytes()
    assert hashlib.sha256(data).hexdigest()==archive['sha256']
    for resource in archive['render_resources']:
        if resource['subtype']!=5:
            continue
        version,flags=struct.unpack_from('<II',data,resource['offset']+8)
        stride=24 if flags&1 and version>0 else 32
        key,parts,vertices,indices=resource['leading_words']
        assert 16+16*parts+stride*vertices+2*indices==resource['payload_size'],resource['name']
        strides[stride]+=1
        checked+=1
trace=root/'runs/model024-ground/render.jsonl'
rows=[json.loads(line) for line in trace.read_text().splitlines()]
loaded={}
matches=[]
ambiguous=0
for row in rows:
    if row['event']=='load':
        loaded[row['record']]=row
        continue
    if not row['index_in_resource']:
        ambiguous+=1
        continue
    source=loaded[row['record']]
    parts=[source['parts'][i:i+4] for i in range(0,len(source['parts']),4)]
    hits=[i for i,p in enumerate(parts)
          if source['vertex_base']+p[2]*source['stride']==row['vertex_address']
          and source['index_base']+p[3]*2==row['index_address']
          and p[1]+2==(row['primitive']&65535)]
    matches.append(dict(name=row['name'],record=row['record'],part_matches=hits))
run=json.loads((trace.parent/'run.json').read_text())
report=dict(archive_layouts_verified=checked,strides=dict(strides),
            trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
            recorded_loads=sum(r['event']=='load' for r in rows),
            ambiguous_vertex_only_draws=ambiguous,
            both_range_samples=len(matches),exact_part_matches=sum(bool(r['part_matches']) for r in matches),
            matches=matches,run_state=run['state'],exit_code=run['exit_code'],timed_out=run['timed_out'])
(root.parent/'outputs/MODEL-024-draw-mapping.json').write_text(json.dumps(report,indent=2)+'\n')
print({k:v for k,v in report.items() if k!='matches'})
assert matches and all(r['part_matches'] for r in matches)
