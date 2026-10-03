"""Verify completed native candidate-capture replay and preserve its hashes."""
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parent.parent
run=root/'work/runs/skin038-capture'
metadata=json.loads((run/'run.json').read_text())
assert metadata['state']=='finished'
replay_passed=metadata['exit_code']==0 and not metadata['timed_out'] and any(
    'VBlank diagnostic stop at 2576' in line for line in metadata['stop_lines'])
submissions=[json.loads(line) for line in (run/'submissions.jsonl').read_text().splitlines()]
transforms=[json.loads(line) for line in (run/'transforms.jsonl').read_text().splitlines()]
complete=[s for s in submissions if s['completed_pose']]
assert complete and all(s['runtime_pose']>0 for s in complete)
assert all(s['runtime_pose']==s['completed_pose'] for s in complete)
assert len({s['runtime_pose'] for s in complete})==len(complete)
assert all(s['part']==20 for s in complete)
assert all(t['pose_serial']>0 for t in transforms if t['name']=='battle_droid' and t['matched'])
log=(run/'native.log').read_text(errors='replace')
assert '[overrides] Skin candidate loaded ' in log
paths=[Path(__file__),run/'run.json',run/'native.log',run/'submissions.jsonl',run/'transforms.jsonl',
       root/'outputs/SKIN-038-tests.log',root/'work/build-windows-native/bin/RenegadeNative.exe']
paths+=list((root/'work/mods-skin038-capture/models/battle_droid').iterdir())
paths+=[root/'work/project/source/profiles/renegade/host'/name for name in
        ['override_skin.cpp','override_skin.hpp','override_pose.hpp','render_resource_trace024.hpp']]
paths+=[root/'work/project/source/profiles/renegade/tests/override_model.cpp']
report=dict(scope='Real candidate loading and runtime pose capture; original character rendering retained.',
            replay_passed=replay_passed,native_run=metadata,submission_samples=len(submissions),complete_runtime_poses=len(complete),
            completed_serials=[s['runtime_pose'] for s in complete],
            matched_droid_draws=sum(t['name']=='battle_droid' and t['matched'] for t in transforms),
            sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
(root/'outputs/SKIN-038-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('native_run','sha256')},indent=2))
raise SystemExit(0 if replay_passed else 1)
