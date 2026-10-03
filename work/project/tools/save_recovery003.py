#!/usr/bin/env python3
"""Save explicit source roots and completed evidence; never includes game/assets/fonts."""
from pathlib import Path
import hashlib,json,zipfile,datetime,sys
root=Path('/mnt/data/renegade');src=root/'intake/sources/PSPRecomp'
name=sys.argv[1] if len(sys.argv)>1 else '003A'
out=Path('/mnt/data')/f'RenegadeSquadron-Checkpoint-{name}-Recovery.zip'
records=[]
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=5) as z:
 def add(p,arc):
  if p.is_symlink() or p.suffix.lower() in {'.ttf','.otf','.woff','.woff2','.fon','.fnt'}:return
  b=p.read_bytes();z.writestr(arc,b);records.append({'path':arc,'size':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 for sub in ['CMakeLists.txt','LICENSE','README.md','include','src','tests','tools','configs','docs','profiles/renegade','profiles/vcs/host']:
  p=src/sub
  if p.is_file():add(p,'source/'+sub)
  elif p.is_dir():
   for f in sorted(p.rglob('*')):
    if f.is_file():add(f,'source/'+str(f.relative_to(src)))
 for sub in ['tools','tests']:
  for p in sorted((root/sub).rglob('*')):
   if p.is_file() and p.suffix in {'.py','.sh','.cpp','.hpp','.json','.md'}:add(p,str(p.relative_to(root)))
 for p in sorted((root/'logs/session003').glob('*.status.json')):
  add(p,'evidence/'+p.name)
  lp=p.with_name(p.name.replace('.status.json','.log'))
  if lp.exists():add(lp,'evidence/'+lp.name)
 p=root/'logs/session003/core-regressions003.log'
 if p.exists():add(p,'evidence/'+p.name)
 md=f'''# Renegade Squadron checkpoint {name}: source recovery\n\nThe scratch container reset after checkpoint 002. Its source/native archive were not persisted; only its historical report/video/image survived. This snapshot restores the original dependency intake and checkpoint 001 source, then reconstructs missing VFPU pack/sort/sign/partial-memory lowering, independent scratchpad mapping, and GE transfer support.\n\nThis is a SOURCE recovery checkpoint, not a completed native build or gameplay verification. The complete native build was in progress at snapshot time; only finished job results are included. Consult evidence/ for actual results. First-level combat, active enemies, completion, save/reload and stability are NOT verified by this snapshot. Windows toolkit remains deferred.\n\nOriginal intake000+001 and the original uploaded game remain required and already available. Source base is PSPRecomp f6e7d415c7f447b934cc3865a31eb725f353d659. Generated code is included for this user's private recompilation work; original BOOT.BIN/ISO/PRX/game assets/fonts and compiler caches are excluded.\n\nRestoration: reassemble the existing intake with its restore_intake.py; bootstrap_scratch.sh supplies the SDK. Replace PSPRecomp source with source/ in this ZIP. See tools/compile003.sh for exact current scratch build invocation. All dependencies must be restored from the original intake; this ZIP does not download them. The early recovery scripts currently use /mnt/data/renegade.\n'''
 z.writestr('CHECKPOINT.md',md)
 z.writestr('manifest.json',json.dumps({'format':'renegade-source-recovery-v1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'first_level_gameplay_verified':False,'files':records},indent=2))
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 manifest=json.loads(z.read('manifest.json'))
 for rec in manifest['files']:
  b=z.read(rec['path']);assert len(b)==rec['size'] and hashlib.sha256(b).hexdigest()==rec['sha256']
sha=hashlib.sha256(out.read_bytes()).hexdigest();out.with_suffix('.sha256').write_text(sha+'  '+out.name+'\n')
print(json.dumps({'path':str(out),'size':out.stat().st_size,'sha256':sha,'verified_files':len(records)}))
