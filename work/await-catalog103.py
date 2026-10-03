"""Wait only for the already-running bounded attempt, then audit its dumps."""
import json,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parent.parent
path=root/'work/runs/coverage103-yavin-campaign-recorded-gpu/run.json'
while True:
 state=json.loads(path.read_text())
 if state['state']=='finished':break
 assert state['state']=='running',state
 if time.time()>state['started_unix']+state['timeout_seconds']+60:
  raise SystemExit('Runner has not sealed terminal state after its timeout; inspect without relaunching.')
 time.sleep(3)
print(json.dumps({'terminal':state['state'],'exit_code':state['exit_code'],'timed_out':state['timed_out']},indent=2),flush=True)
# Failed attempts also retain their original texture provenance explicitly.
raise SystemExit(subprocess.call([sys.executable,str(root/'work/catalog-textures103.py')],cwd=root))
