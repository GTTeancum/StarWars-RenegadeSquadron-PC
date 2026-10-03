"""Catalog exact RSCF names and supported HSKN bones from local disc archives."""
import csv, hashlib, importlib.util, json, struct
from pathlib import Path

root = Path(__file__).resolve().parent.parent
disc = root / 'work/game/disc'
spec = importlib.util.spec_from_file_location('hskn', root / 'work/project/source/profiles/renegade/tools/hskn_skeleton.py')
hskn = importlib.util.module_from_spec(spec); spec.loader.exec_module(hskn)

def string(b, at):
    end = b.find(b'\0', at, min(len(b), at + 513))
    if end < at: raise ValueError('Missing string terminator')
    s = b[at:end].decode('ascii')
    if not s or any(ord(c) < 32 or ord(c) > 126 for c in s): raise ValueError('Invalid name')
    return s, at + ((end-at+4) & ~3)

def scan(path):
    b = path.read_bytes()
    if b[:8] != b'Asura   ': raise ValueError('Not an uncompressed Asura archive')
    records=[]; skeletons={}; rejected=[]; links=[]; at=8
    while at+16 <= len(b):
        size, version, flags = struct.unpack_from('<III', b, at+4)
        if size < 16 or at+size > len(b): raise ValueError(f'Bad chunk at {at}')
        c=b[at:at+size]; tag=c[:4]
        if tag==b'RSCF' and len(c)>=32:
            kind, subtype, length=struct.unpack_from('<III', c, 16)
            if kind==0 and subtype==5:
                name, pos=string(c,28)
                if pos+length!=len(c) or length<16: raise ValueError('Bad model payload')
                key, slots, vertices, indices=struct.unpack_from('<4I', c, pos)
                records.append(dict(name=name, offset=at, key=key, part_slots=slots, vertices=vertices, indices=indices))
        elif tag==b'HSKN':
            try:
                s=hskn.parse_skeleton(c); skeletons[s['name']]=s
            except ValueError as e:
                try: name,_=string(c,24)
                except ValueError: name='unknown'
                rejected.append(dict(name=name, offset=at, reason=str(e)))
        elif tag==b'HSKL':
            base,pos=string(c,16); variant,pos=string(c,pos)
            links.append(dict(base=base, variant=variant, offset=at))
        at+=size
    if b[at:] not in (b'',b'\0'*4): raise ValueError('Unexpected trailer')
    parent={l['variant']:l['base'] for l in links}
    for rec in records:
        name=rec['name']; seen=set()
        while name not in skeletons and name in parent and name not in seen:
            seen.add(name); name=parent[name]
        rec['skeleton_name']=name if name in skeletons else None
        rec['folder_safe']=not any(c in rec['name'] for c in '/\\:') and rec['name'] not in ('.','..')
    return dict(archive=path.relative_to(disc).as_posix(), sha256=hashlib.sha256(b).hexdigest(), models=records, skeletons=skeletons, rejected_skeletons=rejected, lod_links=links)

archives=[]; failures=[]
for p in sorted((disc/'PSP_GAME/USRDIR').rglob('*.PSP')):
    try: archives.append(scan(p))
    except (ValueError, UnicodeError, struct.error) as e: failures.append(dict(archive=p.relative_to(disc).as_posix(),error=str(e)))
report=dict(scope='Archive metadata, not a claim that every resource has been drawn or override-tested', archives=archives, failures=failures)
(root/'outputs/MODEL-CATALOG.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
rows=[]
for a in archives:
    for m in a['models']:
        s=a['skeletons'].get(m['skeleton_name'])
        rows.append(dict(name=m['name'],archive=a['archive'],part_slots=m['part_slots'],vertices=m['vertices'],indices=m['indices'],skeleton=m['skeleton_name'] or '',bones=len(s['bones']) if s else '',folder_safe=m['folder_safe']))
with (root/'outputs/MODEL-CATALOG.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
names=sorted({r['name'] for r in rows},key=str.casefold)
lines=['# Original model names','',f'{len(names)} distinct names; {len(rows)} occurrences in {len(archives)} scanned archives. {len(failures)} archive failures.','',
       'Search this file for a name. The CSV lists its maps, part counts and skeleton availability. The JSON contains exact bone names, slots and bind transforms. Archive presence is not gameplay validation.','',
       'LOD names are separate override folders. Matching names in different archives can have different skeletons; select the intended archive before making bindings.','', '| Exact resource / folder name | Archive occurrences |','| --- | ---: |']
for name in names: lines.append(f'| `{name}` | {sum(r["name"]==name for r in rows)} |')
(root/'outputs/MODEL-NAMES.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(dict(unique_names=len(names),occurrences=len(rows),archives=len(archives),failures=failures,skeletons=sum(len(a['skeletons']) for a in archives),rejected_skeletons=sum(len(a['rejected_skeletons']) for a in archives)),indent=2))
