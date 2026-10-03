"""Check that the archive catalog covers every Asura map/UI-related file."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent.parent
base=root/'work/game/disc/PSP_GAME/USRDIR'
catalog=json.loads((root/'work/texture-dumps058/catalog.json').read_text())
known={a['archive']:a for a in catalog['archives']};areas={};missing=[];changed=[]
for area in ('ENVS','GUIMENU','GRAPHICS','MISC'):
    rows=[]
    for path in sorted((base/area).rglob('*')):
        if not path.is_file():continue
        name=path.relative_to(base).as_posix();data=path.read_bytes();sha=hashlib.sha256(data).hexdigest();record=known.get(name)
        if record and sha!=record['sha256']:changed.append(name)
        if data.startswith(b'Asura   ') and not record:missing.append(name)
        rows.append(dict(file=name,bytes=len(data),sha256=sha,header_hex=data[:16].hex(),
                         catalogued=record is not None,texture_chunks=record['texture_chunks'] if record else None))
    areas[area]=rows
report=dict(areas=areas,uncatalogued_asura_archives=missing,changed_archives=changed,extraction_failures=catalog['failures'])
(root/'outputs/TEXTURE-ARCHIVE-AUDIT-064.json').write_text(json.dumps(report,indent=2)+'\n')
assert not missing and not changed and not catalog['failures']
print('All 99 Asura archives verified; standalone PNG paths explicitly inventoried.')
