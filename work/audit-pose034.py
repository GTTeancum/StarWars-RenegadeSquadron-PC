"""Verify full original pose observations against emitted GE transforms."""
import collections
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parent.parent
folder=root/'work/runs/model034-submissions'
run=json.loads((folder/'run.json').read_text())
assert run['state']=='finished' and run['exit_code']==0 and not run['timed_out']
rows=[json.loads(line) for line in (folder/'submissions.jsonl').read_text().splitlines()]
draws=[r for line in (folder/'transforms.jsonl').read_text().splitlines()
       if (r:=json.loads(line))['name']=='battle_droid']
assert len(rows)==256
assert {r['part'] for r in rows}==set(range(21))
complete=len(rows)//21
for i in range(complete):
    assert [r['part'] for r in rows[i*21:(i+1)*21]]==list(range(21))
by_part=collections.defaultdict(list)
for row in rows: by_part[row['part']].append(row)
seen=collections.Counter();errors=[]
for draw in draws:
    part=draw['part'];source=by_part[part][seen[part]];seen[part]+=1
    m=source['matrix'];c=source['camera']
    expected=[sum(c[k*4+i]*m[j*4+k] for k in range(4)) for j in range(4) for i in range(3)]
    error=max(abs(a-b) for a,b in zip(expected,draw['world']))
    # GE stores matrix floats with their low eight bits discarded; host JSON
    # rounding and original single-precision multiplication also contribute.
    assert error<0.0001,(part,error)
    errors.append(error)
assert len(errors)==60
head_variants=len({tuple(r['matrix']) for r in by_part[6]})
assert head_variants>1
paths=[Path(__file__),root/'outputs/POSE-034-tests.log',
       root/'outputs/CHECKPOINT-034-FULL-POSE-SUBMISSIONS.md',
       root/'work/project/source/profiles/renegade/host/render_resource_trace024.hpp',
       root/'work/project/source/profiles/renegade/tools/patch_asset_hooks.py',
       root/'work/project/source/profiles/renegade/CMakeLists.txt',
       root/'work/project/source/profiles/renegade/generated/generated_unit_0128.cpp',
       root/'Play-RenegadeSquadronPC.ps1',root/'OVERRIDES.md',
       root/'work/build-windows-native/bin/RenegadeNative.exe',
       root/'work/model024-geonosis-replay.txt',
       folder/'run.json',folder/'native.log',folder/'submissions.jsonl',folder/'transforms.jsonl',
       *folder.glob('frames/*.ppm')]
report=dict(run=run,samples=len(rows),complete_pose_batches=complete,
            trailing_partial_batch=len(rows)%21,head_pose_variants=head_variants,
            observed_draw_contexts=sorted({r['registers'][4] for r in rows}),
            callers=sorted({r['caller'] for r in rows}),
            compared_ge_draws=len(errors),max_world_matrix_error=max(errors),
            limitation='Only one draw context observed; multi-instance separation is unverified.',
            hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
(root/'outputs/POSE-034-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('run','hashes')},indent=2))
