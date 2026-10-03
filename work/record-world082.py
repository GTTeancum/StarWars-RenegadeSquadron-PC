"""Record verified converted-map run, assets, build/test evidence and hashes."""
import hashlib,json,re
from pathlib import Path
r=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
run=r/'work/runs/converted082-ordmantell';state=json.loads((run/'run.json').read_text())
assert state['exit_code']==0 and not state['timed_out']
log=(run/'native.log').read_text();assert 'Converted world geometry loaded models=13' in log
draws=re.findall(r'MSH draw converted-world submitted=(\d+) prepared=(\d+) pixels_written=(\d+)',log)
assert draws and any(int(d[2])>0 for d in draws)
tests=(r/'outputs/WORLD-082-tests.log').read_text()
assert tests.count('Test Passed.')==7 and '123 model integration checks passed' in tests
audit=json.loads((r/'outputs/CONVERTED-MAP-082.json').read_text())
assets={}
for obj in audit['objects']:
    if not obj.get('model_loaded'):continue
    model=audit['models'][obj['geometry'].lower()];p=r/model['path']
    assets[p.relative_to(r).as_posix()]=sha(p);assert sha(p)==model['sha256']
    for m in model['materials']:
        if not m['texture']:continue
        p=(r/model['path']).parent/m['texture'];assert sha(p)==m['texture_sha256']
        assets[p.relative_to(r).as_posix()]=sha(p)
files=[r/'work/build-windows-native/bin/RenegadeNative.exe',r/'work/build-windows-native/profiles/renegade/renegade_override_model_tests.exe',r/'outputs/WORLD-082-tests.log',r/'work/world-ordmantell082.txt',r/'Capture-Converted-OrdMantell.ps1',run/'run.json',run/'native.log',run/'world-draws.jsonl']
files+=list((r/'outputs').glob('*082*.png'))
files += [r/'work/project/source/profiles/renegade/host'/name for name in ['override_world.hpp','override_world.cpp']]
report=dict(scope='First converted Ord Mantell static-geometry/material bridge. Partial map coverage, not all maps or a completed mission.',run=state,logged_draw_samples=[dict(submitted=int(a),prepared=int(b),pixels_written=int(c)) for a,b,c in draws],tests=dict(passed=7,model_integration_checks=123,rebuilt=['model','render'],log='outputs/WORLD-082-tests.log'),visual_inspection='On-foot GCW conquest; converted debris/ground/structures visibly differ. Original water/unmatched surfaces remain; poses/AI differ between baseline and converted runs.',authored_assets_unchanged=True,asset_sha256=assets,sha256={p.relative_to(r).as_posix():sha(p) for p in files})
(r/'outputs/WORLD-082-state.json').write_text(json.dumps(report,indent=2)+'\n')
runtime=json.loads((r/'outputs/TEXTURE-RUNTIME-082.json').read_text())
runtime['converted082-ordmantell']['visual_state']=report['visual_inspection']
runtime['converted082-ordmantell']['converted_world_models_loaded']=13
runtime['coverage082-ordmantell']['visual_state']='On-foot GCW conquest baseline with pack 074; no converted world geometry.'
(r/'outputs/TEXTURE-RUNTIME-082.json').write_text(json.dumps(runtime,indent=2)+'\n')
print(json.dumps(dict(verified_assets=len(assets),tests=7,model_checks=123,logged_draw_samples=len(draws),binary_sha256=state['native_binary_sha256']),indent=2))
