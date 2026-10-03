"""Cross-check exact command associations against independent matrix diagnostics."""
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parent.parent;run=root/'work/runs/commands041-fixed'
metadata=json.loads((run/'run.json').read_text())
assert metadata['state']=='finished' and metadata['exit_code']==0 and not metadata['timed_out']
assert any('VBlank diagnostic stop at 2576' in s for s in metadata['stop_lines'])
exe=root/'work/build-windows-native/bin/RenegadeNative.exe'
assert hashlib.sha256(exe.read_bytes()).hexdigest()==metadata['native_binary_sha256']
commands=[json.loads(s) for s in (run/'commands.jsonl').read_text().splitlines()]
transforms=[json.loads(s) for s in (run/'transforms.jsonl').read_text().splitlines()]
assert commands and all(c['pc']%4==0 and c['pose_serial']>0 and c['batch']>0 for c in commands)
assert len({(c['batch'],c['pc']) for c in commands})==len(commands)
keys={(c['pose_serial'],c['slot'],c['vertex_address'],c['index_address'],c['primitive']) for c in commands}
matched=[t for t in transforms if t['name']=='battle_droid' and t['matched'] and t['pose_serial']]
assert matched
for t in matched:
    assert (t['pose_serial'],t['part'],t['vertex_address'],t['index_address'],t['primitive']) in keys,t
expected_slots={t['part'] for t in matched}
batch_slots={}
for c in commands:batch_slots.setdefault(c['batch'],set()).add(c['slot'])
full_batches=sum(slots==expected_slots for slots in batch_slots.values())
assert full_batches>=4
paths=[Path(__file__),exe,run/'run.json',run/'native.log',run/'commands.jsonl',run/'commands.jsonl.debug.jsonl',run/'transforms.jsonl',run/'submissions.jsonl',
       run/'frames/frame_002575.ppm',root/'outputs/COMMAND-041-tests.log',root/'outputs/COMMAND-041-launcher.log']
paths+=[root/'work/project/source/profiles/renegade/host'/p for p in ['override_commands.hpp','override_commands.cpp','render_resource_trace024.hpp','psp_services.cpp']]
paths+=[root/'work/project/source'/p for p in ['profiles/renegade/tests/override_commands.cpp','profiles/renegade/tools/patch_asset_hooks.py',
    'profiles/renegade/CMakeLists.txt','profiles/vcs/host/ge_renderer.cpp','profiles/vcs/host/ge_renderer.hpp','profiles/vcs/host/vcs_profile.cpp',
    'profiles/renegade/generated/generated_unit_0329.cpp']]
paths+=list((root/'work/mods-skin040-retarget/models/battle_droid').iterdir())
report=dict(scope='Exact emitted command to complete pose association. Original character geometry still rendered.',
    native_run=metadata,command_samples=len(commands),independently_matched_draws=len(matched),
    batches=len(batch_slots),batches_with_all_populated_slots=full_batches,max_pose_serial=max(c['pose_serial'] for c in commands),
    populated_slots=sorted({c['slot'] for c in commands}),
    sha256={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()})
(root/'outputs/COMMAND-041-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('native_run','sha256')},indent=2))
