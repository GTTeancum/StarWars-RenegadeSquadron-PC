"""Measure archive identity coverage without conflating mip bindings or runtime traversal."""
import collections,json
from pathlib import Path
root=Path(__file__).resolve().parent.parent
catalog=json.loads((root/'work/texture-dumps058/catalog.json').read_text())
pack=json.loads((root/'outputs/TEXTURE-PACK-071.json').read_text())
bindings={f['id']:f for f in pack['files']}
groups=collections.defaultdict(list)
for t in catalog['textures']:
    if t['mip']==0:groups[t['id']].append(t)
by_archive=[]
for archive in catalog['archives']:
    name=archive['archive'];ids={i for i,records in groups.items() if any(t['archive']==name for t in records)}
    by_archive.append(dict(archive=name,unique_base_images=len(ids),bound_base_images=len(ids&bindings.keys()),unbound_base_ids=sorted(ids-bindings.keys())))
unbound=[dict(id=i,records=records) for i,records in groups.items() if i not in bindings]
report=dict(scope='Archive base-image identities with staged bindings; not visible screen coverage, runtime traversal, or whole-map quality acceptance.',base_image_count=len(groups),bound_base_images=len(groups.keys()&bindings.keys()),unbound_base_images=len(unbound),total_pack_bindings=len(bindings),archives=by_archive,unbound=unbound,decode_failures=catalog['failures'])
(root/'outputs/TEXTURE-COVERAGE-071.json').write_text(json.dumps(report,indent=2)+'\n')
lines=['# Texture coverage at checkpoint 071','','The decoder catalog covers 99 Asura archives. This report counts unique base texture identities per archive; shared identities appear in more than one archive. It does not prove every runtime composite or every on-screen texture has been captured.','',f"Pack 071 binds {report['bound_base_images']} of {len(groups)} distinct archived base images. {len(unbound)} remain unbound. Its {len(bindings)} total bindings include mip images and runtime aliases.",'','| Archive | Base images | Bound |','| --- | ---: | ---: |']
lines += [f"| {a['archive']} | {a['unique_base_images']} | {a['bound_base_images']} |" for a in by_archive]
lines += ['','Remaining base IDs and archive/name/offset provenance are in `TEXTURE-COVERAGE-071.json`. The runtime audit at checkpoint 070 contains 49 unresolved cases; this archive coverage report does not reclassify them.','']
(root/'outputs/TEXTURE-COVERAGE-071.md').write_text('\n'.join(lines))
print(json.dumps({k:v for k,v in report.items() if k not in ['archives','unbound']}))
