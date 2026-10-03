from pathlib import Path
import zipfile,hashlib,json,time
r=Path(__file__).resolve().parent;o=r.parent/'outputs';files=[]
s=json.loads((r/'runs/control-native012a/status.json').read_text());assert s['paused'] and s['vblank']==7263
for rel in ('runs/native012a/run.json','runs/native012a/native.log','runs/control-native012a/commands.log','runs/control-native012a/adaptive011.jsonl','runs/control-native012a/status.json','modern012a-replay.log','adaptive-native012a.log','flight-native012a.log','step011.py','replay-adaptive011.py','flight012.py'):
 files.append((r/rel,'work/'+rel))
for frame in (4957,4969,4986,4991,6041,6606,6633,6771,6904,7052,7116,7132,7240,7263):
 p=o/f'native012a-vblank{frame}.png';files.append((p,p.name))
files.append((o/'flight012-comparison.json','flight012-comparison.json'))
payloads=[(n,p.read_bytes()) for p,n in files]
manifest=[dict(path=n,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in payloads]
out=o/'RenegadeSquadron-Checkpoint-012A-Evidence.zip'
with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
 for n,b in payloads:z.writestr(n,b)
 z.writestr('manifest.json',json.dumps(dict(snapshot_unix=time.time(),status=s,files=manifest),indent=2))
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 for f in manifest:assert hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256']
h=hashlib.sha256(out.read_bytes()).hexdigest();out.with_suffix('.zip.sha256').write_text(h+'  '+out.name+'\n')
print(json.dumps(dict(sha256=h,bytes=out.stat().st_size,payloads=len(files))))
