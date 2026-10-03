from pathlib import Path
import zipfile,hashlib,json
r=Path(__file__).resolve().parent;o=r.parent/'outputs';files=[]
for rel in ('runs/native010c/run.json','runs/native010c/native.log','runs/control-native010c/commands.log','runs/control-native010c/adaptive011.jsonl','runs/control-native010c/status.json','runs/startup011a/results.json','modern010c-replay.log','test-controls011-baseline.log','test-windows011-interaction.log','build-windows011-interaction.log','step011.py','continue011.py'):
 files.append((r/rel,'work/'+rel))
for frame in (4050,4252,4492,4530,4795,4832,4897,4934):
 p=o/f'native010c-vblank{frame}.png';files.append((p,p.name))
manifest=[dict(path=n,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p,n in files]
out=o/'RenegadeSquadron-Checkpoint-011B-Evidence.zip'
with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
 for p,n in files:z.write(p,n)
 z.writestr('manifest.json',json.dumps(manifest,indent=2))
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 for f in manifest:assert hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256']
h=hashlib.sha256(out.read_bytes()).hexdigest();out.with_suffix('.zip.sha256').write_text(h+'  '+out.name+'\n')
print(json.dumps(dict(sha256=h,bytes=out.stat().st_size,payloads=len(files))))
