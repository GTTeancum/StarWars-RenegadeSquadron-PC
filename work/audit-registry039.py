"""Preserve registry benchmark samples and the full native capture replay."""
import hashlib
import json
from pathlib import Path
import statistics

root=Path(__file__).resolve().parent.parent
run=root/'work/runs/skin039-capture'
metadata=json.loads((run/'run.json').read_text())
assert metadata['state']=='finished'
assert hashlib.sha256((root/'work/build-windows-native/bin/RenegadeNative.exe').read_bytes()).hexdigest()==metadata['native_binary_sha256'], 'Build changed since replay; preserve existing historical report instead of pairing it with newer source'
passed=metadata['exit_code']==0 and not metadata['timed_out'] and any(
    'VBlank diagnostic stop at 2576' in s for s in metadata['stop_lines'])
samples={}
for name in ('before','after-range','after'):
    path=root/f'outputs/REGISTRY-039-{name}.jsonl'
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows)==3 and all(r['matches']==0 and r['queries']==10000 and r['records']==4096 for r in rows)
    values=[r['milliseconds'] for r in rows]
    samples[name]=dict(milliseconds=values,median_ms=statistics.median(values))
submissions=[json.loads(line) for line in (run/'submissions.jsonl').read_text().splitlines()]
complete=[s for s in submissions if s['completed_pose']]
assert complete and all(s['runtime_pose']==s['completed_pose'] and s['part']==20 for s in complete)
draws=[json.loads(line) for line in (run/'transforms.jsonl').read_text().splitlines()]
droid=[d for d in draws if d['name']=='battle_droid' and d['matched']]
assert droid and all(d['pose_serial']>0 for d in droid)
paths=[Path(__file__),run/'run.json',run/'native.log',run/'submissions.jsonl',run/'transforms.jsonl',
       root/'outputs/REGISTRY-039-tests.log',root/'work/build-windows-native/bin/RenegadeNative.exe',
       root/'work/project/source/profiles/renegade/CMakeLists.txt',
       root/'work/project/source/profiles/renegade/tests/override_model.cpp']
paths+=list((root/'outputs').glob('REGISTRY-039-*.jsonl'))
paths+=[root/'work/project/source/profiles/renegade/host'/p for p in
        ['override_resource_registry.hpp','override_resource_registry.cpp','render_resource_trace024.hpp','override_skin.cpp']]
paths+=list((run/'frames').glob('*'))
report=dict(scope='Registry performance and runtime pose capture; original character geometry still rendered.',
            benchmark=samples,replay_passed=passed,native_run=metadata,
            complete_runtime_poses=len(complete),matched_droid_draws=len(droid),
            sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()})
(root/'outputs/REGISTRY-039-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('sha256','native_run')},indent=2))
raise SystemExit(0 if passed else 1)
