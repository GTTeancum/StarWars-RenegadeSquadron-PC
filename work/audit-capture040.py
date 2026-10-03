"""Verify the latest runtime-capture replay without claiming replacement drawing."""
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parent.parent;run=root/'work/runs/skin040-capture'
metadata=json.loads((run/'run.json').read_text())
assert metadata['state']=='finished' and metadata['exit_code']==0 and not metadata['timed_out']
assert any('VBlank diagnostic stop at 2576' in s for s in metadata['stop_lines'])
exe=root/'work/build-windows-native/bin/RenegadeNative.exe'
assert hashlib.sha256(exe.read_bytes()).hexdigest()==metadata['native_binary_sha256']
submissions=[json.loads(s) for s in (run/'submissions.jsonl').read_text().splitlines()]
complete=[s for s in submissions if s['completed_pose']]
assert len(complete)==12 and all(s['part']==20 and s['runtime_pose']==s['completed_pose'] for s in complete)
draws=[json.loads(s) for s in (run/'transforms.jsonl').read_text().splitlines()]
droid=[d for d in draws if d['name']=='battle_droid' and d['matched']]
assert len(droid)==60 and all(d['pose_serial']>0 for d in droid)
assert '[overrides] Skin candidate loaded ' in (run/'native.log').read_text(errors='replace')
paths=[Path(__file__),exe,run/'run.json',run/'native.log',run/'submissions.jsonl',run/'transforms.jsonl',run/'frames/frame_002575.ppm']
paths+=list((root/'work/mods-skin038-capture/models/battle_droid').iterdir())
paths+=[root/'work/project/source/profiles/renegade/host'/p for p in
        ['override_resource_registry.hpp','override_resource_registry.cpp','override_skin.cpp','override_pose.hpp','render_resource_trace024.hpp']]
report=dict(scope='Completed native replay with candidate loading and pose capture. Original character rendering remains active.',
            native_run=metadata,complete_runtime_poses=len(complete),matched_droid_draws=len(droid),
            sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()})
(root/'outputs/SKIN-040-capture.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(elapsed_seconds=metadata['elapsed_seconds'],complete_runtime_poses=len(complete),matched_droid_draws=len(droid))))
