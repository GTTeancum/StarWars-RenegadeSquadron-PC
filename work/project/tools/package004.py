#!/usr/bin/env python3
"""Package an explicit source allowlist, matching executable/AOT, and diagnostics.
Original game files, system fonts, RAM dumps, compiler intermediates and SDK
caches are never recursively included. Run only after native sessions finish.
"""
import argparse, datetime, hashlib, json, os, subprocess, zipfile
from pathlib import Path
from verify_checkpoint004 import process
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('/mnt/data/renegade'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=a.root.resolve()
def digest(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
old=json.loads((r/'checkpoint003C/manifest.json').read_text());allowed={}
for record in old['files']:
 if record['path'].startswith('source/'):
  allowed[record['path']]=r/'intake/sources/PSPRecomp'/record['path'][7:]
for name in ['profiles/vcs/host/ge_stencil.hpp','profiles/renegade/tests/stencil004.cpp','profiles/renegade/tests/clock004.cpp']:
 allowed['source/'+name]=r/'intake/sources/PSPRecomp'/name
# Historical helper sources are retained but not run during packaging.
for path in sorted((r/'tools').iterdir()):
 if path.is_file() and path.suffix in ('.py','.sh','.json','.csv','.cpp'):
  allowed['tools/'+path.name]=path
for path in sorted((r/'replays').glob('*.txt')):allowed['replays/'+path.name]=path
for path in sorted(r.glob('CHECKPOINT-004*.md')):allowed[path.name]=path
for path in sorted((r/'logs/session004').iterdir()):
 if path.is_file() and path.suffix in ('.log','.exit','.json'):allowed['evidence/logs/'+path.name]=path
for path in sorted((r/'evidence004').rglob('*')):
 if path.is_file() and path.suffix in ('.png','.mp4','.json','.txt','.md'):
  allowed['evidence/'+path.relative_to(r/'evidence004').as_posix()]=path
for run in sorted((r/'runs').glob('*004*')):
 if not run.is_dir():continue
 if (run/'run.json').is_file():
  status=json.loads((run/'run.json').read_text())
  if status.get('state')=='running':raise SystemExit('Finish native session before packaging: '+run.name)
 for name in ('run.json','native.log','commands.log','status.json','input-replay.txt'):
  path=run/name
  if path.is_file():allowed['evidence/runs/'+run.name+'/'+name]=path
allowed['prebuilt/linux-x86_64/RenegadeNative']=r/'intake/out/native004/bin/RenegadeNative'
allowed['prebuilt/linux-x86_64/librenegade_aot.a']=r/'checkpoint003C/prebuilt/linux-x86_64/librenegade_aot.a'
allowed['prebuilt/aot-binding.json']=r/'tools/aot-binding004.json'
allowed['README.md']=r/'README-004.md'
for name,path in allowed.items():
 if path.suffix.lower() in ('.ttf','.otf','.woff','.woff2','.fnt','.bin','.prx','.iso','.7z') or path.is_symlink() or not path.is_file():raise SystemExit('Disallowed or missing payload: '+str(path))
entries=[];a.output.parent.mkdir(parents=True,exist_ok=True)
temporary=a.output.with_suffix('.partial')
with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
 for name,path in sorted(allowed.items()):
  entries.append({'path':name,'size':path.stat().st_size,'sha256':digest(path),'executable':bool(path.stat().st_mode & 0o111)})
  z.write(path,name)
 z.writestr('manifest.json',json.dumps({'format':'renegade-native-checkpoint-v4','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'first_level_gameplay_verified':False,'windows_verified':False,'files':entries},indent=2)+'\n')
count=process(temporary);temporary.replace(a.output)
sha=digest(a.output);a.output.with_suffix('.sha256').write_text(sha+'  '+a.output.name+'\n')
print(json.dumps({'archive':str(a.output),'bytes':a.output.stat().st_size,'sha256':sha,'verified_payloads':count},indent=2))
