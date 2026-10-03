"""Prepare scoped 103 evidence tools without editing frozen prior checkpoints."""
import re
from pathlib import Path
root=Path(__file__).resolve().parent.parent
def save(name,text):
    p=root/'work'/name
    assert not p.exists(),p
    p.write_text(text)
for name in ['catalog-textures','audit-runtime-textures','build-texture-browser','test-texture-browser','snapshot-source','receipt-source']:
    ext='.cjs' if name=='test-texture-browser' else '.py'
    s=(root/'work'/f'{name}102{ext}').read_text()
    s=s.replace('texture-catalog102','texture-catalog103').replace('-102','-103').replace('checkpoint 102','checkpoint 103')
    if name=='catalog-textures':
        s=s.replace('TEXTURES-101-state','TEXTURES-102-state').replace('texture-catalog101','texture-catalog102')
    if name=='receipt-source':
        s=s.replace('verified 101','verified 102')
    save(f'{name}103{ext}',s)
s=(root/'work/verify-coverage102.py').read_text()
s=s.replace('COVERAGE-102','COVERAGE-103').replace('catalog101','catalog102').replace('observed101','observed102').replace('TEXTURES-101-state','TEXTURES-102-state')
names=['gc-entry','campaign-entry','gc-alliance-board-gpu','gc-alliance-phase2-gpu','gc-alliance-phase2-software','gc-empire-board-gpu','gc-tech-menu-gpu','gc-troops-menu-gpu','yavin-campaign-recorded-gpu']
expected={f'coverage103-{n}':('ENVS/CAMPAIGN/YAVIN_IV.PSP' if n.startswith('yavin') else None if n.startswith('campaign-entry') else 'ENVS/GC.PSP') for n in names}
s=re.sub(r'^expected = .*$', 'expected = '+repr(expected),s,flags=re.M)
s=re.sub(r"^expected\['coverage102-[^\n]+\n",'',s,flags=re.M)
s=s.replace('spawn captures are not full matches, traversal or ship-flight acceptance.','menu probes and legacy campaign replay do not prove modern controls, victory, traversal or ship-flight acceptance.')
save('verify-coverage103.py',s)
s=(root/'work/verify-texture-catalog102.py').read_text()
for a,b in [('texture-catalog102','texture-catalog103'),('COVERAGE-102','COVERAGE-103'),('TEXTURES-102-state','TEXTURES-103-state'),('MUTABILITY-102','MUTABILITY-103'),('CATALOG-102','CATALOG-103'),('TEXTURE-102-browser','TEXTURE-103-browser'),('COVERAGE-102-visual','COVERAGE-103-visual'),('COVERAGE-102.md','COVERAGE-103.md'),('SOURCE-101','SOURCE-102'),('TEXTURES-101-state','TEXTURES-102-state')]:
    s=s.replace(a,b)
s=s.replace('tool-only 102 changes','tool-only 103 changes').replace('New map/era/menu runtime evidence','GC/menu and bounded legacy-campaign runtime evidence')
save('verify-texture-catalog103.py',s)
print('Prepared scoped 103 evidence tools; native sources and existing textures unchanged.')
