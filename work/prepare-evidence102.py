"""Create 102 evidence tools with scoped reference changes; preserve frozen history."""
import re
from pathlib import Path
root=Path(__file__).resolve().parent.parent
def save(name,text):
    p=root/'work'/name
    assert not p.exists(),p
    p.write_text(text)
for name in ['catalog-textures','audit-runtime-textures','build-texture-browser',
             'test-texture-browser','snapshot-source','receipt-source']:
    ext='.cjs' if name=='test-texture-browser' else '.py'
    s=(root/'work'/f'{name}101{ext}').read_text()
    s=s.replace('texture-catalog101','texture-catalog102').replace('-101','-102').replace('checkpoint 101','checkpoint 102')
    if name=='catalog-textures':
        s=s.replace('TEXTURES-100-state','TEXTURES-101-state').replace('texture-catalog100','texture-catalog101')
    if name=='receipt-source':
        s=s.replace('native unchanged from tested 100','native unchanged from tested 100 and verified 101')
    save(f'{name}102{ext}',s)
s=(root/'work/verify-coverage100.py').read_text()
s=s.replace('COVERAGE-100','COVERAGE-102').replace('catalog099','catalog101').replace('observed099','observed101')
s=s.replace("old = json.loads((root / 'work/texture-catalog101/catalog.json').read_text())", """old = json.loads((root / 'work/texture-catalog101/catalog.json').read_text())
baseline_state=json.loads((root/'outputs/TEXTURES-101-state.json').read_text())
assert sha(root/'work/texture-catalog101/catalog.json')==baseline_state['artifact_sha256']['work/texture-catalog101/catalog.json']""")
expected={
 'coverage102-geonosis-era-menu':None,
 'coverage102-mustafar-clone-gpu':'ENVS/PREQUEL/MUSTAFAR.PSP',
 'coverage102-korriban-clone-gpu':'ENVS/PREQUEL/KORRIBAN.PSP',
 'coverage102-saleucami-clone-gpu':'ENVS/PREQUEL/SALEUCAMI.PSP',
 'coverage102-yavin-clone-gpu':'ENVS/PREQUEL/YAVIN_IV.PSP',
 'coverage102-ordmantell-clone-gpu':'ENVS/PREQUEL/ORD_MANTELL.PSP',
 'coverage102-sullust-clone-gpu':'ENVS/PREQUEL/SULLUST.PSP',
 'coverage102-geonosis-gcw-gpu':'ENVS/CLASSIC/GEONOSIS.PSP',
}
s=re.sub(r'^expected = .*$', 'expected = '+repr(expected),s,flags=re.M)
save('verify-coverage102.py',s)
s=(root/'work/verify-texture-catalog101.py').read_text()
s=s.replace('texture-catalog101','texture-catalog102').replace('COVERAGE-101','COVERAGE-102')
s=s.replace('TEXTURES-101-state','TEXTURES-102-state').replace('MUTABILITY-101','MUTABILITY-102')
s=s.replace('CATALOG-101','CATALOG-102').replace('TEXTURE-101-browser','TEXTURE-102-browser')
s=s.replace('SOURCE-100','SOURCE-101').replace('TEXTURES-100-state','TEXTURES-101-state')
s=s.replace('unchanged from verified SOURCE-100','unchanged from verified SOURCE-101')
s=s.replace('Modern movement/fire evidence in COVERAGE-102.json.','New map/era/menu runtime evidence in COVERAGE-102.json.')
s=s.replace('not repeated for tool-only 101 changes','not repeated for tool-only 102 changes')
save('verify-texture-catalog102.py',s)
print('Prepared 102 texture/runtime/source verification tools; no numeric/hash or native changes.')
