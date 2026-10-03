"""Run unmodified real MSH assets through the weighted deformation diagnostic."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parent.parent
exe=root/'work/build-windows-native/profiles/renegade/renegade_override_asset_audit.exe'
env=os.environ.copy();env['PATH']=str(root/'work/windows-sdk/bin')+os.pathsep+env.get('PATH','')
assets=Path('Z:/Modding/SWBF2_Modtools/assets/sides/cis/msh')
results=[]
for name in ('cis_inf_bdroid_low1.msh','cis_inf_bdroid.msh','cis_inf_sbdroid.msh'):
    path=assets/name
    run=subprocess.run([str(exe),'--skin-identity',str(path)],env=env,capture_output=True,text=True)
    results.append(dict(asset=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        exit_code=run.returncode,stdout=run.stdout,stderr=run.stderr))
low=json.loads(results[0]['stdout'])
assert results[0]['exit_code']==0 and low['source_weighted_vertices']>0
assert low['identity_max_error']<1e-5 and low['translation_max_error']<1e-5
assert all(r['exit_code']==1 and 'Unsupported MSH material render type' in r['stderr'] for r in results[1:])
paths=[Path(__file__),exe,root/'outputs/SKIN-036-tests.log',
       root/'outputs/CHECKPOINT-036-WEIGHTED-DEFORMATION.md',
       root/'work/project/source/profiles/renegade/host/override_skin.hpp',
       root/'work/project/source/profiles/renegade/host/override_skin.cpp',
       root/'work/project/source/profiles/renegade/tests/override_skin.cpp',
       root/'work/project/source/profiles/renegade/tests/override_asset_audit.cpp',
       root/'work/project/source/profiles/renegade/CMakeLists.txt',
       root/'work/build-windows-native/bin/RenegadeNative.exe']
report=dict(results=results,
    scope='Identity and common-translation deformation only; no retargeted game rendering or material image loading.',
    hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
(root/'outputs/SKIN-036-real-asset.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(results,indent=2))
