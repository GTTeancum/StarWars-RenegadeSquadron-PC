"""Verify bounded part-matching replay evidence and hash reproducible state."""
import collections
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
reports = {}
paths = [
    'work/audit-model032.py', 'outputs/MODEL-032-tests.log',
    'Play-RenegadeSquadronPC.ps1',
    'work/model024-geonosis-replay.txt',
    'work/build-windows-native/bin/RenegadeNative.exe',
    'work/project/source/profiles/renegade/host/override_resource_registry.hpp',
    'work/project/source/profiles/renegade/host/render_resource_trace024.hpp',
    'work/project/source/profiles/renegade/host/override_model.cpp',
    'work/project/source/profiles/renegade/tests/override_model.cpp',
    'work/project/source/profiles/vcs/host/ge_renderer.cpp',
]
for name in ('model032-candidates', 'model032-resolved'):
    folder = root / 'work/runs' / name
    run = json.loads((folder / 'run.json').read_text())
    assert run['state'] == 'finished' and run['exit_code'] == 0 and not run['timed_out']
    rows = [json.loads(line) for line in (folder / 'transforms.jsonl').read_text().splitlines()]
    droid = [r for r in rows if r['name'] == 'battle_droid']
    assert droid
    first = {r['part']: r for r in reversed(droid)}
    reports[name] = {
        'run': run, 'samples': len(rows),
        'matching_counts': dict(collections.Counter(str(r['matched']) for r in rows)),
        'battle_droid_first_samples': list(first.values()),
    }
    for path in [folder/'run.json', folder/'native.log', folder/'transforms.jsonl', *folder.glob('frames/*.ppm')]:
        paths.append(path.relative_to(root).as_posix())

fixed = reports['model032-resolved']['battle_droid_first_samples']
expected = {1, 3, 4, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20}
assert {r['part'] for r in fixed if r['matched']} == expected
assert all(r['matched'] for r in fixed)
report = {'runs': reports, 'hashes': {
    path: hashlib.sha256((root/path).read_bytes()).hexdigest() for path in paths}}
(root/'outputs/MODEL-032-summary.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({name: {k: v for k, v in result.items() if k != 'battle_droid_first_samples' and k != 'run'}
                  for name, result in reports.items()}, indent=2))
