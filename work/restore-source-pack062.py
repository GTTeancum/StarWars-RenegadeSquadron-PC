"""Restore the exact local texture pack from its manifest and supplied sources."""
import hashlib,json,shutil
from pathlib import Path
root=Path(__file__).resolve().parent.parent
manifest=json.loads((root/'outputs/TEXTURE-PACK-062.json').read_text())
pack=root/'work/mods-textures-source062'
if pack.exists():raise SystemExit('Existing pack preserved; this command is for restoring a missing pack.')
pending=[]
for row in manifest['files']:
    src=(root/row['source']).resolve();dst=(root/row['replacement']).resolve()
    if not src.is_relative_to(root) or not dst.is_relative_to(pack):raise SystemExit('Manifest path outside expected root')
    if hashlib.sha256(src.read_bytes()).hexdigest()!=row['sha256']:raise SystemExit(f'Source hash mismatch: {src}')
    pending.append((src,dst,row['sha256']))
for src,dst,digest in pending:
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
    assert hashlib.sha256(dst.read_bytes()).hexdigest()==digest
print(f'Restored and verified {len(pending)} supplied-texture bindings.')
