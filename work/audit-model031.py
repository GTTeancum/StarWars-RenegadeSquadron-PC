"""Retain terminal live-registry evidence and build state."""
import hashlib,json,re
from pathlib import Path
root=Path(__file__).resolve().parent.parent
folder=root/'work/runs/model031-registry'
run=json.loads((folder/'run.json').read_text())
assert run['state']=='finished' and run['exit_code']==0 and not run['timed_out']
draws=[dict(zip(('submitted','prepared','pixels_written'),map(int,m))) for m in
       re.findall(r'MSH draw .* submitted=(\d+) prepared=(\d+) pixels_written=(\d+)',(folder/'native.log').read_text(errors='replace'))]
assert any(d['pixels_written']>0 for d in draws)
paths=['work/audit-model031.py','outputs/MODEL-031-tests.log',
       'work/project/source/profiles/renegade/host/override_resource_registry.hpp',
       'work/project/source/profiles/renegade/host/render_resource_trace024.hpp',
       'work/project/source/profiles/renegade/host/override_model.cpp',
       'work/project/source/profiles/renegade/tests/override_model.cpp',
       'work/build-windows-native/bin/RenegadeNative.exe','work/model024-geonosis-replay.txt']
paths += [p.relative_to(root).as_posix() for p in folder.glob('frames/*.ppm')]
paths += [p.relative_to(root).as_posix() for p in (folder/'run.json',folder/'native.log')]
report={'run':run,'sampled_draws':draws,'hashes':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in paths}}
(root/'outputs/MODEL-031-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'elapsed':run['elapsed_seconds'],'draws':draws},indent=2))
