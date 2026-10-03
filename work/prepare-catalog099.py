"""Derive new evidence tools while keeping prior checkpoint files frozen."""
import re
from pathlib import Path
root=Path(__file__).resolve().parent.parent
for name in ['catalog-textures','audit-runtime-textures','build-texture-browser','test-texture-browser',
             'verify-texture-catalog','snapshot-source','receipt-source']:
    extension = '.cjs' if name == 'test-texture-browser' else '.py'
    source=(root/'work'/f'{name}098{extension}').read_text().replace('098','099')
    if name == 'verify-texture-catalog':
        source=source.replace('SOURCE-097-manifest.json','SOURCE-098-manifest.json')
        source=source.replace("== 798", ">= 798")
    target=root/'work'/f'{name}099{extension}'
    assert not target.exists(),target
    target.write_text(source)
source=(root/'work/verify-coverage098.py').read_text().replace('098','099')
source=source.replace('catalog097','catalog098').replace('observed097','observed098')
source=source.replace('texture-catalog097','texture-catalog098')
expected={
 'coverage099-planet-space-yavin':None,
 'coverage099-era-space-yavin':None,
 'coverage099-kashyyyk-gcw-conquest-gpu':'ENVS/CLASSIC/KASHYYYK.PSP',
 'coverage099-mygeeto-gcw-conquest-gpu':'ENVS/CLASSIC/MYGEETO.PSP',
 'coverage099-tatooine-gcw-conquest-gpu':'ENVS/CLASSIC/TATOOINE.PSP',
 'coverage099-space-kashyyyk-gcw-assault-gpu':'ENVS/CLASSIC/SPACE_KASHYYYK_CIVIL.PSP',
 'coverage099-space-yavin-gcw-assault-gpu':'ENVS/CLASSIC/SPACE_YAVIN.PSP',
}
source=re.sub(r'^expected = .*$', 'expected = '+repr(expected),source,flags=re.M)
target=root/'work/verify-coverage099.py'
assert not target.exists()
target.write_text(source)
print('Prepared new catalog, coverage, verification and snapshot tools.')
