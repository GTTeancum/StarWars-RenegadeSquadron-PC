"""Replay the observed post-capture approach using controller inputs only."""
import json,time,subprocess,sys
from pathlib import Path
r=Path(__file__).resolve().parent;name=sys.argv[1];deadline=time.monotonic()+1200
while time.monotonic()<deadline:
 try:
  s=json.loads((r/'runs'/('control-'+name)/'status.json').read_text())
  if s['paused'] and s['vblank']==4252:break
 except (OSError,json.JSONDecodeError):pass
 time.sleep(.2)
else:raise TimeoutError('Tutorial endpoint not reached')
for args in [('240',),('8','--psp','16384'),('30',),('40','--ly','22000'),('5',),('30','--buttons','4')]:
 subprocess.run([sys.executable,str(r/'step011.py'),name,*args],check=True)
print('Interaction attempt complete. Inspect actual output; no automatic gameplay verdict.',flush=True)
