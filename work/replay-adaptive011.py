"""Replay recorded controller actions into a fresh paused run, with no state injection."""
import argparse,json,time,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('record',type=Path);p.add_argument('--through',type=int,required=True);a=p.parse_args()
r=Path(__file__).resolve().parent;rows=[json.loads(t) for t in a.record.read_text().splitlines() if t.strip()]
rows=[t for t in rows if t['end']<=a.through]
assert rows and len(rows)<10000
for n,t in enumerate(rows):
 assert 0<t['end']-t['start']<=2000
 if n:assert rows[n-1]['end']==t['start']
deadline=time.monotonic()+1800
while time.monotonic()<deadline:
 try:
  s=json.loads((r/'runs'/('control-'+a.run)/'status.json').read_text())
  if s['paused'] and s['vblank']==rows[0]['start']:break
 except (OSError,json.JSONDecodeError):pass
 time.sleep(.2)
else:raise TimeoutError('Replay start not reached')
for row in rows:
 args=[sys.executable,str(r/'step011.py'),a.run,str(row['end']-row['start'])]
 for k in ('connected','lx','ly','rx','ry','lt','rt','buttons','psp'):
  args.extend(['--'+k,str(row.get(k,1 if k=='connected' else 0))])
 for k in ('psp_x','psp_y'):args.extend(['--'+k.replace('_','-'),str(row.get(k,128))])
 subprocess.run(args,check=True)
print('Recorded inputs complete; actual gameplay must be inspected.',flush=True)
