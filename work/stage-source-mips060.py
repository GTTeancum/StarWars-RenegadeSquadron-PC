"""Stage reviewed source files for verified archive base and mip identities."""
import hashlib,json,shutil
from pathlib import Path
root=Path(__file__).resolve().parent.parent
accepted=json.loads((root/'outputs/TEXTURE-PACK-059.json').read_text())['accepted']
catalog=json.loads((root/'work/texture-dumps058/catalog.json').read_text())
pack=root/'work/mods-textures-source060'
if pack.exists():raise SystemExit('Output exists; preserve it and choose a new pack version.')
by_base={a['id']:a for a in accepted}
groups={}
for rec in catalog['textures']:
    if rec['mip']==0 and rec['id'] in by_base:groups[(rec['archive'],rec['offset'])]=by_base[rec['id']]
pending={};conflicts=[]
for rec in catalog['textures']:
    source=groups.get((rec['archive'],rec['offset']))
    if not source:continue
    candidate=pending.setdefault(rec['id'],{'source':source,'occurrences':[]})
    if candidate['source']['replacement_sha256']!=source['replacement_sha256']:
        conflicts.append({'id':rec['id'],'reason':'Different reviewed source files share this original mip identity'})
    candidate['occurrences'].append(rec)
conflicting={c['id'] for c in conflicts}
(pack/'textures').mkdir(parents=True)
written=[]
for identity,candidate in pending.items():
    if identity in conflicting:continue
    source=candidate['source'];path=root/source['source']['paths'][0]
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest==source['replacement_sha256']
    dest=pack/'textures'/(identity+path.suffix.lower());shutil.copyfile(path,dest)
    written.append({'id':identity,'source':path.relative_to(root).as_posix(),'replacement':dest.relative_to(root).as_posix(),'sha256':digest,'original_occurrences':candidate['occurrences']})
report={'scope':'Partial source-only pack; base and selected-mip identities mapped through exact archive chunk provenance','base_matches':len(accepted),'files':written,'conflicts':conflicts}
(root/'outputs/TEXTURE-PACK-060.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'base_matches':len(accepted),'replacement_ids':len(written),'conflicts':len(conflicts)},indent=2))
