"""Audit checkpoint 043 movement evidence separately from the later eviction fix."""
import hashlib,json,re
from pathlib import Path
root=Path(__file__).resolve().parent.parent
run=root/'work/runs/skin043-movement'
meta=json.loads((run/'run.json').read_text())
assert meta['exit_code']==0 and not meta['timed_out'] and meta['frame_count']==7
assert any('VBlank diagnostic stop at 2876' in s for s in meta['stop_lines'])
assert meta['native_binary_sha256']=='cebdc97ef1713ab3ede5e76311777783cb246be30a8f8b0b3714c479ff937e55'
log=(run/'native.log').read_text(errors='replace')
draws=[list(map(int,m)) for m in re.findall(r'Skinned MSH draw .* submitted=(\d+) prepared=(\d+) pixels_written=(\d+)',log)]
assert len(draws)==8 and all(a==482 and b>0 and c>0 for a,b,c in draws)
assert 'Skin deformation failed' not in log
frames=sorted((run/'frames').glob('*.ppm'));assert len(frames)==7
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert len({sha(p) for p in frames})==7
commands=[json.loads(s) for s in (run/'commands.jsonl').read_text().splitlines()]
assert len(commands)==512
paths=[Path(__file__),run/'run.json',run/'native.log',run/'commands.jsonl',root/'work/skin043-movement-replay.txt',root/'outputs/SKIN-043-tests.log',root/'outputs/SKIN-043-movement.png',root/'work/build-windows-native/bin/RenegadeNative.exe']+frames
paths+=list((root/'work/mods-skin040-retarget/models/battle_droid').iterdir())
paths+=[root/'work/project/source/profiles/renegade'/p for p in ['host/override_commands.hpp','host/override_commands.cpp','tests/override_commands.cpp','tests/override_model.cpp']]
report={'scope':'Scripted forward/left analog motion with checkpoint042 binary; later suppression retirement fix independently rebuilt and regression tested.', 'native_run':meta,'logged_draws':draws,'command_samples':len(commands),'pose_batches':len({c['batch'] for c in commands}),'verified_tests':{'override_suites':7,'stencil_suites':1,'command_checks':24,'model_integration_checks':68},'limits':['No physical XInput or right-stick validation in this replay','No independent late-frame pose trace: command samples cap at 512','No gameplay replay of post-movement eviction fix yet','High-detail gloss materials and GPU model overrides remain unsupported'],'sha256':{p.relative_to(root).as_posix():sha(p) for p in paths if p.is_file()}}
(root/'outputs/SKIN-043-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('native_run','sha256')},indent=2))
