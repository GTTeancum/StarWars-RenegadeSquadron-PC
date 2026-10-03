"""Apply recorded-length modern flight height probes after the verified replay endpoint."""
from pathlib import Path
import json,time,subprocess,sys
r=Path(__file__).resolve().parent;name=sys.argv[1];deadline=time.monotonic()+1800
while time.monotonic()<deadline:
 try:
  s=json.loads((r/'runs'/('control-'+name)/'status.json').read_text())
  if s['paused'] and s['vblank']==4957:break
 except (OSError,json.JSONDecodeError):pass
 time.sleep(.2)
else:raise TimeoutError('Flight probe start was not reached')
for args in [('12','--buttons','2048'),('5',),('12','--buttons','4096'),('5',)]:
 subprocess.run([sys.executable,str(r/'step011.py'),name,*args],check=True)
print('Modern height inputs applied; inspect frames and action traces before judging flight.',flush=True)
