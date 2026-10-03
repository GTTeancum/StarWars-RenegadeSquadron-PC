from pathlib import Path
import hashlib,json,zipfile
r=Path(__file__).resolve().parent;o=r.parent/'outputs';files={};cases=[]
specs=[('a','Boz Pity','Galactic Civil War','Conquest',1592),('b','Geonosis','Clone Wars','Conquest',1528),('c','Space Coruscant','Clone Wars','Assault',1736),('d','Space Alderaan','Galactic Civil War','1-Flag CTF',1736),('e','Echo Base','Galactic Civil War','2-Flag CTF',1592),('f','Kashyyyk','Clone Wars','Hero CTF',1608)]
for suffix,mapname,era,mode,frame in specs:
 name='instant015'+suffix;state=json.loads((r/'runs'/name/'run.json').read_text())
 assert state['exit_code']==4 and not state['timed_out']
 assert any('invalid internal function entry' in s and '08A2E2E4' in s for s in state['stop_lines'])
 cases.append(dict(run=name,map=mapname,era=era,mode=mode,spawn_reached=False,exit_code=4,timeout=False,stop=state['stop_lines'],binary_sha256=state['native_binary_sha256']))
 for rel in (f'runs/{name}/run.json',f'runs/{name}/native.log',f'runs/{name}/input-replay.txt',f'runs/control-{name}/commands.log',f'runs/control-{name}/adaptive011.jsonl',f'runs/control-{name}/status.json'):
  files['work/'+rel]=r/rel
 p=o/f'{name}-vblank{frame}.png';files['frames/'+p.name]=p
(o/'INSTANT-ACTION-015-baseline.json').write_text(json.dumps(cases,indent=2)+'\n')
for rel in ('instant015-entry-disassembly.txt','instant015-boot.txt','launch-instant015.ps1','menu015.py','step011.py','verify-relocation015.py','configure-relocation015-fresh.log','runs/relocation015/results.json','package015.py'):
 files['work/'+rel]=r/rel
for n in ('CHECKPOINT-015-RELOCATION-AND-INSTANT-ACTION.md','INSTANT-ACTION-015-baseline.json','RELOCATION-015-manifest.json'):files[n]=o/n
out=o/'RenegadeSquadron-Checkpoint-015-Relocation-Instant-Action.zip';manifest=[]
with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
 for name,p in files.items():
  b=p.read_bytes();z.writestr(name,b);manifest.append(dict(path=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
 z.writestr('manifest.json',json.dumps(dict(files=manifest),indent=2))
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 for row in manifest:assert hashlib.sha256(z.read(row['path'])).hexdigest()==row['sha256']
h=hashlib.sha256(out.read_bytes()).hexdigest();out.with_suffix('.zip.sha256').write_text(h+'  '+out.name+'\n')
print(json.dumps(dict(bytes=out.stat().st_size,payloads=len(manifest),sha256=h)))
