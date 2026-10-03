"""Audit immutable pose completion and deferred GE association in native replay."""
import collections
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parent.parent
folder=root/'work/runs/model035-poses'
run=json.loads((folder/'run.json').read_text())
assert run['state']=='finished' and run['exit_code']==0 and not run['timed_out']
submissions=[json.loads(line) for line in (folder/'submissions.jsonl').read_text().splitlines()]
draws=[r for line in (folder/'transforms.jsonl').read_text().splitlines()
       if (r:=json.loads(line))['name']=='battle_droid']
poses={};pending=[]
for row in submissions:
    if row['part']==0:pending=[]
    pending.append(row)
    if row['completed_pose']:
        assert [r['part'] for r in pending]==list(range(21))
        poses[row['completed_pose']]=pending
assert len(poses)==12
assert len(draws)==60
assert all(r['pose_serial'] in poses for r in draws)
groups=collections.defaultdict(list);maximum=0
for draw in draws:
    serial=draw['pose_serial'];part=draw['part'];source=poses[serial][part]
    m=source['matrix'];c=source['camera']
    expected=[sum(c[k*4+i]*m[j*4+k] for k in range(4)) for j in range(4) for i in range(3)]
    error=max(abs(a-b) for a,b in zip(expected,draw['world']))
    assert error<0.0001
    maximum=max(maximum,error);groups[serial].append(part)
expected_parts={1,3,4,8,9,10,12,13,14,15,16,17,18,19,20}
assert len(groups)==4 and all(set(parts)==expected_parts and len(parts)==15 for parts in groups.values())
paths=[Path(__file__),root/'outputs/POSE-035-tests.log',
       root/'outputs/CHECKPOINT-035-IMMUTABLE-POSES.md',
       root/'work/project/source/profiles/renegade/host/override_pose.hpp',
       root/'work/project/source/profiles/renegade/host/render_resource_trace024.hpp',
       root/'work/project/source/profiles/renegade/tests/override_pose.cpp',
       root/'work/project/source/profiles/renegade/CMakeLists.txt',
       root/'work/build-windows-native/bin/RenegadeNative.exe',
       root/'work/build-windows-native/profiles/renegade/renegade_override_pose_tests.exe',
       root/'work/model024-geonosis-replay.txt',
       folder/'run.json',folder/'native.log',folder/'submissions.jsonl',folder/'transforms.jsonl',
       *folder.glob('frames/*.ppm')]
report=dict(run=run,completed_poses=len(poses),associated_draws=len(draws),
            parts_by_pose=dict(groups),maximum_matrix_error=maximum,
            limitation='One real character observed; multiple contexts verified only by focused tests.',
            hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
(root/'outputs/POSE-035-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('run','hashes')},indent=2))
