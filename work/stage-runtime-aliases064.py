"""Stage only exact-RGB observed runtime aliases; preserve their original alpha."""
import hashlib,json,shutil
from pathlib import Path
root=Path(__file__).resolve().parent.parent
audit=json.loads((root/'outputs/TEXTURE-RUNTIME-AUDIT-064.json').read_text())
old=json.loads((root/'outputs/TEXTURE-PACK-063.json').read_text())
pack=root/'work/mods-textures-source064'
if pack.exists():raise SystemExit('Existing pack preserved.')
aliases=audit['eligible_exact_rgb_aliases'];assert aliases
files={f['id']:dict(f) for f in old['files']}
for a in aliases:
    assert a['id'] not in files
    assert hashlib.sha256((root/a['source']).read_bytes()).hexdigest()==a['sha256']
    assert all(files[i]['sha256']==a['sha256'] for i in a['source_binding_ids'])
shutil.copytree(root/'work/mods-textures-source063',pack)
for a in aliases:
    image=pack/'textures'/(a['id']+Path(a['source']).suffix.lower());shutil.copyfile(root/a['source'],image)
    policy=pack/'textures'/(a['id']+'.json');policy.write_text('{"alpha":"original"}\n')
    files[a['id']]=dict(a,policy_sha256=hashlib.sha256(policy.read_bytes()).hexdigest())
for f in files.values():
    f['replacement']=(pack/'textures'/(f['id']+Path(f['source']).suffix.lower())).relative_to(root).as_posix()
    assert hashlib.sha256((root/f['replacement']).read_bytes()).hexdigest()==f['sha256']
    if 'policy_sha256' in f:
        f['policy']=(pack/'textures'/(f['id']+'.json')).relative_to(root).as_posix()
        assert hashlib.sha256((root/f['policy']).read_bytes()).hexdigest()==f['policy_sha256']
report=dict(scope='Checkpoint 063 sources plus observed exact-RGB runtime aliases; no fuzzy matching',
            aliases=aliases,files=list(files.values()))
(root/'outputs/TEXTURE-PACK-064.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'{len(files)} image bindings; {len(aliases)} verified runtime aliases')
