from pathlib import Path
import zipfile,hashlib,json
r=Path(__file__).resolve().parent;o=r.parent/'outputs';files=[]
for rel in ('runs/native011b/run.json','runs/native011b/native.log','runs/control-native011b/commands.log','runs/control-native011b/adaptive011.jsonl','runs/control-native011b/status.json','runs/startup012/results.json','modern011b-replay.log','adaptive-native011b.log','test-controls012-baseline.log','test-windows012.log','build-windows012.log','step011.py','replay-adaptive011.py'):
 files.append((r/rel,'work/'+rel))
for frame in (4605,4801,4881,4914,4957,4969,4986,4991,5006):
 p=o/f'native011b-vblank{frame}.png';files.append((p,p.name))
files.append((o/'RECOVERY-012-test-detail.log','RECOVERY-012-test-detail.log'))
manifest=[dict(path=n,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p,n in files]
out=o/'RenegadeSquadron-Checkpoint-012-Evidence.zip'
with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
 for p,n in files:z.write(p,n)
 z.writestr('manifest.json',json.dumps(manifest,indent=2))
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 for f in manifest:assert hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256']
h=hashlib.sha256(out.read_bytes()).hexdigest();out.with_suffix('.zip.sha256').write_text(h+'  '+out.name+'\n')
print(json.dumps(dict(sha256=h,bytes=out.stat().st_size,payloads=len(files))))
