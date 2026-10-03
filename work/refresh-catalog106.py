"""Refresh catalog only after all planned gameplay validation is accepted."""
import json,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parent.parent
deadline=time.monotonic()+1200
while not (root/'outputs/UPSCALER-106-gameplay.json').exists():
 assert time.monotonic()<deadline,'Gameplay receipt absent; inspect validation logs before proceeding'
 time.sleep(5)
for script in ['catalog-textures106.py','audit-runtime-textures106.py','build-texture-browser106.py']:
 subprocess.run([sys.executable,str(root/'work'/script)],cwd=root,check=True)
node=Path('C:/Users/LRPC/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe')
with (root/'outputs/TEXTURE-106-browser-tests.txt').open('w') as f:
 subprocess.run([str(node),'work/test-texture-browser106.cjs'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
subprocess.run([sys.executable,'work/verify-texture-catalog106.py'],cwd=root,check=True)
print('Refreshed catalog and original identities verified',flush=True)
