"""Verify high-detail weighted MSH movement replay and preserve hashes."""
import hashlib,json,re
from pathlib import Path
root=Path(__file__).resolve().parent.parent;run=root/'work/runs/skin046-high-detail'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
meta=json.loads((run/'run.json').read_text())
assert meta['state']=='finished' and not meta['timed_out'] and meta['exit_code']==0
assert any('VBlank diagnostic stop at 2876' in s for s in meta['stop_lines'])
assert meta['native_binary_sha256']=='8b0b9e4e0c392cb205bf8cd25cdb1835fa4b2ce100cd7178c93bacfbcd339be5'
log=(run/'native.log').read_text(errors='replace')
draws=[list(map(int,m)) for m in re.findall(r'Skinned MSH draw .* submitted=(\d+) prepared=(\d+) pixels_written=(\d+)',log)]
assert len(draws)==8 and all(a==1378 and b>0 and c>0 for a,b,c in draws),draws
assert 'Skin deformation failed' not in log
frames=sorted((run/'frames').glob('*.ppm'));assert len(frames)==7 and len({sha(p) for p in frames})==7
rest=json.loads((root/'outputs/RETARGET-046-rest.json').read_text())
assert rest['exit_code']==0 and rest['wrong_scale_control']['exit_code']==1
assert json.loads(rest['stdout'])['bind_reconstruction_max_error']<1e-5
paths=[Path(__file__),root/'work/retarget-droid046.py',root/'outputs/RETARGET-046-rest.json',run/'run.json',run/'native.log',root/'work/skin043-movement-replay.txt']+frames
paths+=list((root/'work/mods-skin046-high-detail/models/battle_droid').iterdir())
report=dict(scope='High-detail SWBF2 droid movement replay; appearance requires separate visual review',native_run=meta,logged_draws=draws,rest_max_error=json.loads(rest['stdout'])['bind_reconstruction_max_error'],max_joint_distance=rest['max_joint_distance'],sha256={p.relative_to(root).as_posix():sha(p) for p in paths if p.is_file()})
(root/'outputs/SKIN-046-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('native_run','sha256')},indent=2))
