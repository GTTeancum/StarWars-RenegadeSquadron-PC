#!/usr/bin/env python3
"""Cumulative, verified native checkpoint. No original game assets or fonts.
The 004E source allowlist is retained and supplemented by this session's code.
This packages actual results and never treats an exit code as game acceptance.
"""
import argparse,datetime,hashlib,json,os,zipfile
from pathlib import Path
from verify_checkpoint004 import process
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('/mnt/data/renegade'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=a.root.resolve()
def digest(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
old=json.loads((r/'restored004/manifest.json').read_text());allowed={}
for rec in old['files']:
 name=rec['path']
 if name.startswith('source/'):allowed[name]=r/'intake/sources/PSPRecomp'/name[7:]
for name in ['profiles/renegade/host/display_ui.hpp','profiles/renegade/tests/display005.cpp','profiles/renegade/tests/clock004.cpp','profiles/renegade/host/message_dialog.hpp','profiles/renegade/tests/message005.cpp']:
 allowed['source/'+name]=r/'intake/sources/PSPRecomp'/name
for d in ['tools','replays']:
 for path in sorted((r/d).iterdir()):
  if path.is_file() and path.suffix in ('.py','.sh','.json','.csv','.cpp','.txt','.xml'):allowed[d+'/'+path.name]=path
for p in (r/'restored004').glob('CHECKPOINT-*.md'):allowed['history/'+p.name]=p
for p in r.glob('CHECKPOINT-*.md'):allowed[p.name]=p
for p in (r/'logs/session005').rglob('*'):
 if p.is_file() and p.suffix in ('.log','.exit','.json','.txt'):allowed['evidence/logs/'+p.relative_to(r/'logs/session005').as_posix()]=p
for p in (r/'evidence005').rglob('*'):
 if p.is_file() and p.suffix in ('.png','.mp4','.json','.jsonl','.txt','.md','.csv'):allowed['evidence/'+p.relative_to(r/'evidence005').as_posix()]=p
for run in (r/'runs').glob('*005*'):
 if not run.is_dir():continue
 if (run/'run.json').is_file() and json.loads((run/'run.json').read_text()).get('state')=='running':
  raise SystemExit('Stop or finish native diagnostic before publishing: '+run.name)
 for name in ['run.json','native.log','commands.log','status.json','input-replay.txt']:
  p=run/name
  if p.is_file():allowed['evidence/runs/'+run.name+'/'+name]=p
allowed['prebuilt/linux-x86_64/RenegadeNative']=r/'intake/out/native004/bin/RenegadeNative'
allowed['prebuilt/linux-x86_64/librenegade_aot.a']=r/'prebuilt/linux-x86_64/librenegade_aot.a'
allowed['prebuilt/aot-binding.json']=r/'tools/aot-binding004.json'
allowed['README.md']=r/'README-005.md'
entries=[]
for name,path in sorted(allowed.items()):
 if path.suffix.lower() in ('.ttf','.otf','.woff','.woff2','.fnt','.bin','.prx','.iso','.7z') or path.is_symlink() or not path.is_file():raise SystemExit('Disallowed or missing payload: '+str(path))
 entries.append(dict(path=name,size=path.stat().st_size,sha256=digest(path),executable=bool(path.stat().st_mode&0o111)))
manifest=dict(format='renegade-native-checkpoint-v4',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),first_level_gameplay_verified=False,windows_verified=False,files=entries)
a.output.parent.mkdir(parents=True,exist_ok=True);tmp=a.output.with_suffix('.partial')
with zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
 for entry in entries:z.write(allowed[entry['path']],entry['path'])
 z.writestr('manifest.json',json.dumps(manifest,indent=2)+'\n')
count=process(tmp);tmp.replace(a.output);sha=digest(a.output);a.output.with_suffix('.sha256').write_text(sha+'  '+a.output.name+'\n')
print(json.dumps(dict(archive=str(a.output),size_bytes=a.output.stat().st_size,sha256=sha,payloads=count),indent=2))
