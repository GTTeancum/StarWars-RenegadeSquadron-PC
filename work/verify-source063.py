"""Verify source identities, exact files/policies and completed gameplay captures."""
import hashlib,json,re
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent.parent
pack=json.loads((root/'outputs/TEXTURE-PACK-063.json').read_text());by={f['id']:f for f in pack['files']}
hashes={}
def digest(path):
    value=hashlib.sha256(path.read_bytes()).hexdigest();hashes[path.relative_to(root).as_posix()]=value;return value
for f in pack['files']:
    original=root/'work/texture-dumps058/textures'/(f['id']+'.png');im=Image.open(original).convert('RGBA')
    identity='tex-v1-'+hashlib.sha256(im.width.to_bytes(4,'little')+im.height.to_bytes(4,'little')+im.tobytes()).hexdigest()
    assert identity==f['id']
    assert digest(root/f['source'])==digest(root/f['replacement'])==f['sha256']
    if 'policy' in f:
        assert digest(root/f['policy'])==f['policy_sha256']
        assert json.loads((root/f['policy']).read_text())=={'alpha':'original'}
runs={}
for name,frame in [('echo',2639),('space',2783)]:
    folder=root/f'work/runs/source063-{name}'
    status=json.loads((folder/'run.json').read_text());assert status['state']=='finished' and status['exit_code']==0 and not status['timed_out']
    log=(folder/'native.log').read_text();loaded=sorted(set(re.findall(r'\[overrides\] texture (tex-v1-[a-f0-9]+) loaded',log)))
    alpha=sorted(set(re.findall(r'\[overrides\] texture (tex-v1-[a-f0-9]+) loaded alpha=original',log)))
    assert 'fxaa=1 output=1280x720' in log
    for kind in ('render-720p','render-720p-fxaa'):
        path=folder/f'frames/{kind}/frame_{frame:06d}.ppm';image=Image.open(path);assert image.size==(1280,720)
        dest=root/f'outputs/SOURCE-063-{name}-{kind}.png';image.save(dest);digest(dest)
    runs[name]={'run':status,'loaded':[by[i] for i in loaded],'original_alpha_loaded':alpha}
assert runs['echo']['original_alpha_loaded'],'Gameplay must exercise original-alpha binding'
(root/'outputs/SOURCE-063-runtime.json').write_text(json.dumps(runs,indent=2)+'\n')
paths=list((root/'outputs').glob('*063*.json'))+list((root/'outputs').glob('*063*.md'))+list((root/'outputs').glob('TESTS-063*.txt'))
paths+=list((root/'work').glob('*063*.py'))+[root/'Play-RenegadeSquadronPC.ps1',root/'Capture-Texture-Baseline.ps1',root/'OVERRIDES.md']
paths+=[root/'work/build-windows-native/bin/RenegadeNative.exe']
paths+=[root/p for p in ['work/project/source/profiles/renegade/host/override_store.cpp','work/project/source/profiles/renegade/host/override_texture.hpp','work/project/source/profiles/vcs/host/ge_renderer.cpp','work/project/source/profiles/renegade/tests/override_render.cpp']]
for path in paths:
    if path.name!='TEXTURES-063-state.json':digest(path)
(root/'outputs/TEXTURES-063-state.json').write_text(json.dumps({'original_content_ids_verified':len(pack['files']),'sha256':hashes},indent=2)+'\n')
print(json.dumps({k:{'seconds':v['run']['elapsed_seconds'],'loaded':len(v['loaded']),'original_alpha_loaded':len(v['original_alpha_loaded'])} for k,v in runs.items()},indent=2))
