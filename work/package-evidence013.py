from pathlib import Path
import zipfile,hashlib,json,time
r=Path(__file__).resolve().parent;o=r.parent/'outputs';files=[]
run=json.loads((r/'runs/native012a/run.json').read_text());assert run['exit_code']==0
for rel in ('runs/native012a/run.json','runs/native012a/native.log','runs/control-native012a/commands.log','runs/control-native012a/adaptive011.jsonl','runs/control-native012a/status.json','build-turret013-baseline.log','test-turret013-baseline.log','build-windows013.log','test-windows013.log','build-windows-native/Testing/Temporary/LastTest.log','runs/startup013/results.json','inspect-input013.py','step011.py','replay-adaptive011.py'):
 files.append((r/rel,'work/'+rel))
for p in sorted((r/'runs/native012a').glob('input-inspection-*.json')):files.append((p,'work/runs/native012a/'+p.name))
for frame in (6606,6771,7240,7938,7979,8099,8111,8119,8127,8131,8149,8157):
 p=o/f'native012a-vblank{frame}.png';files.append((p,p.name))
payloads=[(n,p.read_bytes()) for p,n in files]
manifest=[dict(path=n,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in payloads]
out=o/'RenegadeSquadron-Checkpoint-013-Evidence.zip'
with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
 for n,b in payloads:z.writestr(n,b)
 z.writestr('manifest.json',json.dumps(dict(snapshot_unix=time.time(),files=manifest),indent=2))
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 for f in manifest:assert hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256']
h=hashlib.sha256(out.read_bytes()).hexdigest();out.with_suffix('.zip.sha256').write_text(h+'  '+out.name+'\n')
print(json.dumps(dict(sha256=h,bytes=out.stat().st_size,payloads=len(files))))
