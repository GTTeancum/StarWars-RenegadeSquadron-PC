from pathlib import Path
import zipfile,hashlib,json,time
r=Path(__file__).resolve().parent;o=r.parent/'outputs';files=[]
s=json.loads((r/'runs/control-native013a/status.json').read_text());assert s['paused']
for rel in ('runs/native013a/run.json','runs/native013a/native.log','runs/control-native013a/commands.log','runs/control-native013a/adaptive011.jsonl','runs/control-native013a/status.json','replay-native013a.log','step011.py','replay-adaptive011.py'):
 files.append((r/rel,'work/'+rel))
for frame in (9948,10270,10462,10478,10554,10924,11168,11348,11508,12083,12383,s['vblank']):
 p=o/f'native013a-vblank{frame}.png'
 if (p,p.name) not in files:files.append((p,p.name))
payloads=[(n,p.read_bytes()) for p,n in files]
manifest=[dict(path=n,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in payloads]
out=o/'RenegadeSquadron-Checkpoint-013B-Evidence.zip'
with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
 for n,b in payloads:z.writestr(n,b)
 z.writestr('manifest.json',json.dumps(dict(snapshot_unix=time.time(),status=s,files=manifest),indent=2))
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 for f in manifest:assert hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256']
h=hashlib.sha256(out.read_bytes()).hexdigest();out.with_suffix('.zip.sha256').write_text(h+'  '+out.name+'\n')
print(json.dumps(dict(sha256=h,bytes=out.stat().st_size,payloads=len(files),status=s)))
