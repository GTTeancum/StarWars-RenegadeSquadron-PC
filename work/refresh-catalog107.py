"""Refresh originals and final pack provenance after all107 gameplay routes."""
import subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
assert (root/'outputs/UPSCALER-107-gameplay.json').exists()
for script in ['catalog-textures107.py','audit-runtime-textures107.py','build-texture-browser107.py']:
 subprocess.run([sys.executable,str(root/'work'/script)],cwd=root,check=True)
node=Path('C:/Users/LRPC/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe')
with (root/'outputs/TEXTURE-107-browser-tests.txt').open('w') as f:subprocess.run([str(node),'work/test-texture-browser107.cjs'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
subprocess.run([sys.executable,'work/verify-texture-catalog107.py'],cwd=root,check=True)
print('Catalog107 originals, provenance and browser code checks passed')
