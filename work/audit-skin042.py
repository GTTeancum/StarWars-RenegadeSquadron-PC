"""Verify real weighted replacement rendering and preserve reproducible evidence."""
import hashlib
import json
from pathlib import Path
import re

root=Path(__file__).resolve().parent.parent;run=root/'work/runs/skin042-render'
meta=json.loads((run/'run.json').read_text());exe=root/'work/build-windows-native/bin/RenegadeNative.exe'
assert meta['state']=='finished' and meta['exit_code']==0 and not meta['timed_out']
assert any('VBlank diagnostic stop at 2576' in s for s in meta['stop_lines'])
assert hashlib.sha256(exe.read_bytes()).hexdigest()==meta['native_binary_sha256']
log=(run/'native.log').read_text(errors='replace')
draws=[dict(submitted=int(a),prepared=int(b),pixels_written=int(c)) for a,b,c in
       re.findall(r'\[overrides\] Skinned MSH draw .* submitted=(\d+) prepared=(\d+) pixels_written=(\d+)',log)]
assert len(draws)==8 and all(d['submitted']==482 and d['prepared']>0 and d['pixels_written']>0 for d in draws)
assert 'Skin deformation failed' not in log
commands=[json.loads(s) for s in (run/'commands.jsonl').read_text().splitlines()]
transforms=[json.loads(s) for s in (run/'transforms.jsonl').read_text().splitlines()]
keys={(c['pose_serial'],c['slot'],c['vertex_address'],c['index_address'],c['primitive']) for c in commands}
matched=[t for t in transforms if t['name']=='battle_droid' and t['matched'] and t['pose_serial']]
assert len(matched)==60 and all((t['pose_serial'],t['part'],t['vertex_address'],t['index_address'],t['primitive']) in keys for t in matched)
frames=sorted((run/'frames').glob('*.ppm'));assert len(frames)==4
paths=[Path(__file__),exe,run/'run.json',run/'native.log',run/'commands.jsonl',run/'transforms.jsonl',
       run/'submissions.jsonl',root/'outputs/SKIN-042-tests.log']+frames
paths+=list((root/'work/mods-skin040-retarget/models/battle_droid').iterdir())
paths+=[root/'work/project/source/profiles/renegade/host'/p for p in ['override_commands.hpp','override_commands.cpp','override_skin.hpp','override_skin.cpp']]
paths+=[root/'work/project/source/profiles/renegade/tests'/p for p in ['override_commands.cpp','override_skin.cpp','override_model.cpp']]
paths+=[root/'work/project/source/profiles/vcs/host/ge_renderer.cpp']
report=dict(scope='Experimental low-detail SWBF2 droid rendered using original game poses. Broader movement, alignment, LOD and multi-actor validation still needed.',
            native_run=meta,logged_draws=draws,command_samples=len(commands),independently_matched_draws=len(matched),
            pose_batches=len({c['batch'] for c in commands}),
            sha256={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()})
(root/'outputs/SKIN-042-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('native_run','sha256')},indent=2))
