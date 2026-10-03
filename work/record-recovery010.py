"""Record current source and local dependency provenance without changing either."""
from pathlib import Path
import argparse,hashlib,json,datetime,re
p=argparse.ArgumentParser();p.add_argument('--revision',default='010');a=p.parse_args()
if not re.fullmatch(r'[0-9A-Za-z]+',a.revision):p.error('Invalid revision')
root=Path(__file__).resolve().parent
def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
baseline=root/'checkpoint009/source'
current=root/'project/source'
records=[]
for p in sorted(current.rglob('*')):
    if p.is_file():
        rel=p.relative_to(current).as_posix()
        old=baseline/rel
        records.append(dict(path=rel,size=p.stat().st_size,sha256=sha(p),baseline_sha256=sha(old) if old.is_file() else None))
result={'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source':records,'changed':[r['path'] for r in records if r['sha256']!=r['baseline_sha256']],
        'dependencies':[]}
for p in sorted((root/'windows-deps').glob('*.zip')):
    result['dependencies'].append(dict(file=p.name,size=p.stat().st_size,sha256=sha(p),provenance=json.loads(p.with_name(p.name+'.provenance.json').read_text(encoding='utf-8-sig'))))
out=root.parent/f'outputs/RECOVERY-{a.revision}-source-and-dependencies.json'
out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'source_files':len(records),'changed':result['changed'],'record':str(out)}))
