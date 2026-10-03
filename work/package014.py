from pathlib import Path
import hashlib,json,zipfile
r=Path(__file__).resolve().parent;o=r.parent/'outputs';files={}
def add(p,n):
 assert p.is_file(),p
 assert n not in files,n
 files[n]=p
for name in ('CHECKPOINT-014-COMPLETE.md','ACCEPTANCE-014.json','RenegadeSquadron-Recovery-013-Windows-Source.zip','RECOVERY-013-source-and-dependencies.json','RECOVERY-010-sdk-reproduction.json'):
 add(o/name,name)
for p in sorted(o.glob('*.md')):
 if p.name!='CHECKPOINT-014-COMPLETE.md':add(p,'history/'+p.name)
add(r/'build-windows-native/bin/RenegadeNative.exe','native/RenegadeNative.exe')
for rel in ('runs/native013a/run.json','runs/native013a/native.log','runs/native013a/input-replay.txt','runs/control-native013a/commands.log','runs/control-native013a/adaptive011.jsonl','runs/control-native013a/status.json','replay-native013a.log','build-windows013.log','test-windows013.log','test-turret013-baseline.log','build-windows-native/Testing/Temporary/LastTest.log','runs/startup013/results.json','audit014.py','package014.py','step011.py','replay-adaptive011.py'):
 add(r/rel,'work/'+rel)
for v in (6606,7938,7979,8099,9948,10554,11168,11348,12383,12693,12881,12973,13306,13555,13843,14018,14178,14318,14498):
 p=o/f'native013a-vblank{v}.png';add(p,'frames/'+p.name)
manifest=[]
out=o/'RenegadeSquadron-Checkpoint-014-First-Mission-Complete.zip'
with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
 for name,p in files.items():
  data=p.read_bytes();z.writestr(name,data)
  manifest.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
 z.writestr('manifest.json',json.dumps(dict(format='renegade-completed-mission-checkpoint-014',files=manifest),indent=2)+'\n')
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 for f in manifest:assert hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256'],f['path']
with out.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
out.with_suffix('.zip.sha256').write_text(h+'  '+out.name+'\n')
result=dict(archive=out.name,bytes=out.stat().st_size,payloads=len(manifest),sha256=h,crc_passed=True,payload_hashes_passed=True)
(o/'CHECKPOINT-014-package-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
