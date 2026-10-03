"""Stage a local manifest referencing unmodified, verified converted map assets."""
import hashlib,json
from pathlib import Path
r=Path(__file__).resolve().parent.parent
audit=json.loads((r/'outputs/CONVERTED-MAP-082.json').read_text())
names=sorted({o['geometry'].lower() for o in audit['objects'] if o.get('model_loaded')})
paths=[r/audit['models'][name]['path'] for name in names]
assert len(paths)==13
for name,path in zip(names,paths):
    assert hashlib.sha256(path.read_bytes()).hexdigest()==audit['models'][name]['sha256']
    for material in audit['models'][name]['materials']:
        if material['texture']:
            texture=path.parent/material['texture']
            assert hashlib.sha256(texture.read_bytes()).hexdigest()==material['texture_sha256']
manifest=r/'work/world-ordmantell082.txt'
manifest.write_text('RS_WORLD 1 0.8333333333333333 -0.8333333333333333 -0.8333333333333333 13\n'+'\n'.join(json.dumps(p.as_posix()) for p in paths)+'\n')
print(manifest)
