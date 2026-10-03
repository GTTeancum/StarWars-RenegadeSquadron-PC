"""Prepare checkpoint 100 evidence tools, keeping frozen 099 artifacts intact."""
import re
from pathlib import Path
root=Path(__file__).resolve().parent.parent
binary='924ae90a2ed8141bb418df07203100912bb08176eb987b3a834819a49a68e2ec'
for name in ['catalog-textures','audit-runtime-textures','build-texture-browser','test-texture-browser',
             'verify-texture-catalog','snapshot-source','receipt-source']:
    ext='.cjs' if name=='test-texture-browser' else '.py'
    source=(root/'work'/f'{name}099{ext}').read_text().replace('099','100')
    if name=='catalog-textures':
        source=source.replace("outputs/TEXTURES-098-state.json", "outputs/TEXTURES-099-state.json")
        source=source.replace("prior = root/'work/texture-catalog098'", "prior = root/'work/texture-catalog099'")
    if name=='verify-texture-catalog':
        source=source.replace('SOURCE-098-manifest.json','SOURCE-099-manifest.json')
        source=source.replace('572c9e0754a939acbc9e4a76da92ad50e76b11245a173fe53fc99f680d38e164',binary)
        source=source.replace('outputs/FOG-097-final-build-tests.txt','outputs/FOG-100-final-build-tests.txt')
        source=source.replace('outputs/FOG-097-before-tests.txt','outputs/FOG-100-before-test.txt')
        source=source.replace('outputs/FOG-097-test-detail.txt','outputs/FOG-100-test-detail.txt')
    target=root/'work'/f'{name}100{ext}'
    assert not target.exists(),target
    target.write_text(source)
source=(root/'work/verify-coverage099.py').read_text().replace('099','100')
source=source.replace('catalog098','catalog099').replace('observed098','observed099')
source=source.replace('texture-catalog098','texture-catalog099')
source=source.replace('572c9e0754a939acbc9e4a76da92ad50e76b11245a173fe53fc99f680d38e164',binary)
expected={
 'coverage100-hoth-gcw-software':'ENVS/CLASSIC/HOTH.PSP',
 'coverage100-hoth-gcw-gpu':'ENVS/CLASSIC/HOTH.PSP',
 'coverage100-mygeeto-clone-software':'ENVS/PREQUEL/MYGEETO.PSP',
 'coverage100-mygeeto-clone-gpu':'ENVS/PREQUEL/MYGEETO.PSP',
}
source=re.sub(r'^expected = .*$', 'expected = '+repr(expected),source,flags=re.M)
target=root/'work/verify-coverage100.py'
assert not target.exists()
target.write_text(source)
print('Prepared checkpoint 100 evidence tools.')
