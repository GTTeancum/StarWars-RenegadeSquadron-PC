"""Apply recorded original menu button taps, preserving the normal step recorder."""
import argparse,json,subprocess,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('buttons',nargs='+',type=int);a=p.parse_args()
r=Path(__file__).resolve().parent;pad=r/'runs'/('gamepad-'+a.run+'.txt')
deadline=time.monotonic()+180
while not (r/'runs'/('control-'+a.run)/'status.json').exists():
 if time.monotonic()>deadline:raise TimeoutError('No menu pause')
 time.sleep(.2)
if not pad.exists():pad.write_text('0 1 0 0 0 0 0 0 0\n')
for mask in a.buttons:
 for m in (mask,0):
  result=subprocess.run([sys.executable,str(r/'step011.py'),a.run,'8','--psp',str(m)],capture_output=True,text=True)
  if result.returncode:raise RuntimeError(result.stdout+result.stderr)
s=json.loads((r/'runs'/('control-'+a.run)/'status.json').read_text());print(json.dumps(s));print(str(r.parent/'outputs'/f"{a.run}-vblank{s['vblank']}.png"))
