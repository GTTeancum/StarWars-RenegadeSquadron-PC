from pathlib import Path
import zipfile,hashlib,json
r=Path(__file__).resolve().parent;o=r.parent/'outputs';files=[]
for rel in ('runs/native011a/run.json','runs/native011a/native.log','runs/control-native011a/commands.log','runs/control-native011a/adaptive011.jsonl','runs/control-native011a/status.json','runs/control-native011a/status.json.tmp','runs/startup011c/results.json','modern011a-replay.log','continue-native011a.log','test-context011c.log','test-windows011c.log','build-windows011c.log','step011.py','continue011.py','replay-adaptive011.py'):
 files.append((r/rel,'work/'+rel))
for frame in (3854,4500,4605,4717,4733,4801,4819):
 p=o/f'native011a-vblank{frame}.png';files.append((p,p.name))
manifest=[dict(path=n,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p,n in files]
out=o/'RenegadeSquadron-Checkpoint-011C-Evidence.zip'
with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
 for p,n in files:z.write(p,n)
 z.writestr('manifest.json',json.dumps(manifest,indent=2))
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 for f in manifest:assert hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256']
h=hashlib.sha256(out.read_bytes()).hexdigest();out.with_suffix('.zip.sha256').write_text(h+'  '+out.name+'\n')
print(json.dumps(dict(sha256=h,bytes=out.stat().st_size,payloads=len(files))))
