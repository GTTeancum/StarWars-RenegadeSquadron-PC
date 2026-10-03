"""Stage visually reviewed supplied Hoth artwork, preserving source bytes."""
import hashlib, json, shutil
from pathlib import Path

root = Path(__file__).resolve().parent.parent
rows = json.loads((root/'outputs/SOURCE-061-candidates.json').read_text())
catalog = json.loads((root/'work/texture-dumps058/catalog.json').read_text())['textures']
old = json.loads((root/'outputs/TEXTURE-PACK-060-reviewed.json').read_text())
pack = root/'work/mods-textures-source061'
if pack.exists():
    raise SystemExit('Preserve existing pack; choose a new version.')
shutil.copytree(root/'work/mods-textures-source060-reviewed', pack)
# Visual review: corresponding panels/UV islands, direct RGB; opaque assets only.
# Tauntaun has incompatible islands. FX/console alpha needs material semantics.
accepted = [1,2,5,7,8,9,10,12,13,14,15,16,17,18,19,20,21,22,23,24]
bindings = {}
for i in accepted:
    row = rows[i]
    keys = {(r['archive'],r['offset']) for r in catalog if r['mip']==0 and r['id']==row['id']}
    for rec in catalog:
        if (rec['archive'],rec['offset']) not in keys: continue
        source = row['source']['paths'][0]
        prior = bindings.setdefault(rec['id'], source)
        if prior != source: raise RuntimeError('Conflicting source mapping')
files = {f['id']:dict(f) for f in old['files']}
for identity, source in bindings.items():
    src = root/source
    dst = pack/'textures'/(identity+src.suffix.lower())
    shutil.copyfile(src,dst)
    files[identity] = dict(id=identity,source=source,sha256=hashlib.sha256(src.read_bytes()).hexdigest())
for f in files.values():
    f['replacement'] = (pack/'textures'/(f['id']+Path(f['source']).suffix.lower())).relative_to(root).as_posix()
    assert hashlib.sha256((root/f['replacement']).read_bytes()).hexdigest()==f['sha256']
report = dict(scope='Supplied source artwork, no AI upscale; reviewed Hoth additions',accepted_review_rows=accepted,
              held_review_rows=[0,3,4,6,11],channel_operation='none',files=list(files.values()))
(root/'outputs/TEXTURE-PACK-061.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'{len(files)} source texture bindings; {len(bindings)} Hoth base/mip bindings')
