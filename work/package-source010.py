"""Package the Windows recovery source and reproducible scripts; excludes game data."""
from pathlib import Path
import argparse,hashlib,json,zipfile,re
p=argparse.ArgumentParser();p.add_argument('--revision',default='010');a=p.parse_args()
if not re.fullmatch(r'[0-9A-Za-z]+',a.revision):p.error('Invalid revision')
root=Path(__file__).resolve().parent
out=root.parent/'outputs'
members=[]
for folder in ('project/source','project/replays'):
    for p in sorted((root/folder).rglob('*')):
        if p.is_file():members.append((p,p.relative_to(root).as_posix()))
for rel in ('configure-windows.cmd','build-windows.cmd','test-windows.cmd','restore-windows-dependencies.ps1','launch-cold010.ps1','check-startup010.py','step011.py','continue011.py','replay-adaptive011.py','project/tools/run010.py','project/tools/replay_controls009.py','project/tools/replay_controls010.py'):
    members.append((root/rel,rel))
manifest=[]
for rel in ('inspect-input013.py','flight012.py'):
    members.append((root/rel,rel))
for p,name in members:
    with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
    manifest.append(dict(path=name,size=p.stat().st_size,sha256=h))
archive=out/f'RenegadeSquadron-Recovery-{a.revision}-Windows-Source.zip'
if archive.exists():raise FileExistsError(archive)
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
    for p,name in members:z.write(p,name)
    z.writestr('manifest010.json',json.dumps({'format':'renegade-source-recovery-010','files':manifest},indent=2)+'\n')
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for row in manifest:
        assert hashlib.sha256(z.read(row['path'])).hexdigest()==row['sha256']
with archive.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
(out/(archive.name+'.sha256')).write_text(h+'  '+archive.name+'\n')
print(json.dumps(dict(path=str(archive),sha256=h,payloads=len(manifest),size=archive.stat().st_size)))
