"""Restore local source texture bytes and reviewed alpha policies from manifest."""
import hashlib,json,shutil
from pathlib import Path
root=Path(__file__).resolve().parent.parent
manifest=json.loads((root/'outputs/TEXTURE-PACK-072.json').read_text())
pack=root/'work/mods-textures-source072'
if pack.exists():raise SystemExit('Existing pack preserved.')
pending=[];policies=[]
for f in manifest['files']:
    src=(root/f['source']).resolve();dst=(root/f['replacement']).resolve()
    assert src.is_relative_to(root) and dst.is_relative_to(pack)
    assert hashlib.sha256(src.read_bytes()).hexdigest()==f['sha256']
    pending.append((src,dst,f['sha256']))
    if 'policy' in f:
        path=(root/f['policy']).resolve();assert path.is_relative_to(pack)
        data=(json.dumps({'alpha':f['alpha']},separators=(',',':'))+'\n').encode()
        assert hashlib.sha256(data).hexdigest()==f['policy_sha256'];policies.append((path,data))
for src,dst,digest in pending:
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
    assert hashlib.sha256(dst.read_bytes()).hexdigest()==digest
for path,data in policies:path.write_bytes(data)
print(f'Restored {len(pending)} image bindings and {len(policies)} alpha policies')
