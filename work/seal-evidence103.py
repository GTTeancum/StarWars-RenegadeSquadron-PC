"""Sequential terminal-evidence checks, documentation and independent receipt."""
import subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
node=Path('C:/Users/LRPC/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe')
steps=[
 ('audit-runtime-textures103.py','MUTABILITY-103-verification.txt'),
 ('build-texture-browser103.py','BROWSER-103-build.txt'),
 ('test-texture-browser103.cjs','TEXTURE-103-browser-tests.txt'),
 ('verify-texture-catalog103.py','TEXTURES-103-verification.txt'),
 ('refresh-texture-guide103.py','GUIDE-103-refresh.txt'),
 ('finalize-checkpoint103.py','CHECKPOINT-103-finalize.txt'),
 ('snapshot-source103.py','SOURCE-103-snapshot.txt'),
 ('receipt-source103.py','SOURCE-103-verification.txt')]
for script,log in steps:
 print(f'Checking {script}',flush=True)
 target=root/'outputs'/log
 assert not target.exists(),f'Preserve previous execution logs: {target}'
 command=[str(node) if script.endswith('.cjs') else sys.executable,str(root/'work'/script)]
 with target.open('w',encoding='utf-8') as output:
  result=subprocess.call(command,cwd=root,stdout=output,stderr=subprocess.STDOUT)
 if result:raise SystemExit(f'{script} failed ({result}); inspect {target}; later steps were not run.')
print('103 evidence, root guide, source ZIP and independent receipt verified. Goal remains incomplete.',flush=True)
