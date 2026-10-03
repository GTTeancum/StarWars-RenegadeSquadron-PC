from pathlib import Path
import hashlib,json,time
source=Path(r'C:/Users/LRPC/Documents/Codex/2026-09-22/referenced-chatgpt-conversation-this-is-an-2')
target=Path(r'D:/Programming/GitHub/RenegadeSquadronPC')
assert source.resolve()!=target.resolve()
files=sorted(p for p in source.rglob('*') if p.is_file())
rows=[]
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
for i,p in enumerate(files):
 rel=p.relative_to(source);q=target/rel
 assert q.is_file(),str(rel)
 a=digest(p);b=digest(q)
 assert p.stat().st_size==q.stat().st_size and a==b,str(rel)
 rows.append(dict(path=rel.as_posix(),bytes=p.stat().st_size,sha256=a))
 if i%2000==0:print('Verified',i,'of',len(files),flush=True)
result=dict(source=str(source),destination=str(target),verified_unix=time.time(),files=len(rows),bytes=sum(x['bytes'] for x in rows),all_sha256_match=True,entries=rows)
(target/'outputs/RELOCATION-015-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='entries'}))
