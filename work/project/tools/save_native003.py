#!/usr/bin/env python3
"""Preserve exact native build, generated source and completed evidence, with hash/CRC checks."""
from pathlib import Path
import hashlib,json,zipfile,datetime,sys,subprocess
R=Path('/mnt/data/renegade');S=R/'intake/sources/PSPRecomp';B=R/'intake/out/renegade'
name=sys.argv[1];out=Path('/mnt/data')/f'RenegadeSquadron-Checkpoint-{name}-Native.zip'
md=R/f'CHECKPOINT-{name}.md';assert md.is_file()
records=[]
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=5) as z:
 def add(p,arc):
  if p.is_symlink() or p.suffix.lower() in {'.ttf','.otf','.woff','.woff2','.fon','.fnt'}:return
  h=hashlib.sha256()
  with p.open('rb') as f,z.open(arc,'w',force_zip64=True) as target:
   while b:=f.read(2**20):target.write(b);h.update(b)
  records.append({'path':arc,'size':p.stat().st_size,'sha256':h.hexdigest()})
 for sub in ['CMakeLists.txt','LICENSE','README.md','include','src','tests','tools','configs','docs','profiles/renegade','profiles/vcs/host']:
  p=S/sub
  if p.is_file():add(p,'source/'+sub)
  elif p.is_dir():
   for f in sorted(p.rglob('*')):
    if f.is_file():add(f,'source/'+str(f.relative_to(S)))
 for sub in ['tools','tests','replays']:
  for p in sorted((R/sub).rglob('*')):
   if p.is_file() and p.suffix in {'.py','.sh','.cpp','.hpp','.json','.md','.txt','.csv'}:add(p,str(p.relative_to(R)))
 for p in sorted((R/'logs/session003').glob('*.status.json')):
  add(p,'evidence/builds/'+p.name);lp=p.with_name(p.name.replace('.status.json','.log'))
  if lp.is_file():add(lp,'evidence/builds/'+lp.name)
 for directory in sorted((R/'runs').iterdir()):
  if (directory/'run.json').is_file() or (directory/'paused-evidence.json').is_file():
   for p in sorted(directory.iterdir()):
    if p.name in {'native.log','run.json','input-replay.txt','external-stop.json','paused-evidence.json'} or p.suffix=='.png':add(p,'evidence/runs/'+directory.name+'/'+p.name)
 for directory in sorted(R.glob('control003-*')):
  # These are controller input records and actual framebuffer captures only.
  for p in sorted(directory.iterdir()):
   if p.is_file() and (p.name in {'commands.log','status.json'} or p.suffix in {'.png','.ppm'}):
    add(p,'evidence/controller/'+directory.name+'/'+p.name)
 for p in sorted((R/'analysis').glob('*003*.json')):
  add(p,'evidence/analysis/'+p.name)
 add(md,'CHECKPOINT.md')
 add(B/'bin/RenegadeNative','prebuilt/linux-x86_64/RenegadeNative')
 add(B/'profiles/renegade/librenegade_aot.a','prebuilt/linux-x86_64/librenegade_aot.a')
 toolchain={'compiler':subprocess.check_output(['g++','--version'],text=True),'target':subprocess.check_output(['g++','-dumpmachine'],text=True).strip(),'ldd':subprocess.check_output(['ldd',str(B/'bin/RenegadeNative')],text=True)}
 z.writestr('prebuilt/toolchain.json',json.dumps(toolchain,indent=2))
 z.writestr('manifest.json',json.dumps({'format':'renegade-native-checkpoint-v1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'first_level_gameplay_verified':False,'files':records},indent=2))
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 for record in json.loads(z.read('manifest.json'))['files']:
  h=hashlib.sha256();n=0
  with z.open(record['path']) as f:
   while b:=f.read(2**20):h.update(b);n+=len(b)
  assert n==record['size'] and h.hexdigest()==record['sha256'],record['path']
h=hashlib.sha256()
with out.open('rb') as f:
 while b:=f.read(2**20):h.update(b)
out.with_suffix('.sha256').write_text(h.hexdigest()+'  '+out.name+'\n')
print(json.dumps({'path':str(out),'size':out.stat().st_size,'sha256':h.hexdigest(),'verified_files':len(records)}))
