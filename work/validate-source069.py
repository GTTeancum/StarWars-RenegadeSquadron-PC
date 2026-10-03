"""Verify pack provenance and production lookup for every new binding."""
import hashlib,json,os,subprocess
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent.parent
manifest=json.loads((root/'outputs/TEXTURE-PACK-069.json').read_text())
old={f['id'] for f in json.loads((root/'outputs/TEXTURE-PACK-068.json').read_text())['files']}
env=os.environ.copy()
env['PATH']=str(root/'work/windows-sdk/bin')+os.pathsep+env['PATH']
env['RENEGADE_OVERRIDE_ROOT']=str(root/'work/mods-textures-source069')
results=[]
for f in manifest['files']:
    for key,digest in [('source','sha256'),('replacement','sha256'),('policy','policy_sha256')]:
        if key in f:assert hashlib.sha256((root/f[key]).read_bytes()).hexdigest()==f[digest]
    if f['id'] in old:continue
    original=root/'work/texture-dumps058/textures'/(f['id']+'.png')
    probe=subprocess.run([str(root/'work/build-windows-native/profiles/renegade/renegade_override_asset_audit.exe'),'--resolve-texture',str(original)],env=env,capture_output=True,text=True,check=True)
    result=json.loads(probe.stdout)
    assert result['matched'] and result['original_alpha']
    a=Image.open(original).convert('RGB');b=Image.open(root/f['source']).convert('RGB')
    results.append(dict(id=f['id'],source=f['source'],probe=result,original_dimensions=a.size,source_dimensions=b.size,original_rgb_colors=len(set(a.getdata())),source_rgb_colors=len(set(b.getdata()))))
out=dict(verified_bindings=len(manifest['files']),verified_alpha_policies=sum('policy' in f for f in manifest['files']),new_binding_probes=results)
(root/'outputs/TEXTURE-VALIDATION-069.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(verified_bindings=out['verified_bindings'],verified_alpha_policies=out['verified_alpha_policies'],new_binding_probes=len(results))))
