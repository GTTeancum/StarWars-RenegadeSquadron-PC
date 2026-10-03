#!/usr/bin/env python3
"""Continue a paused native diagnostic using only contiguous recorded inputs."""
import argparse,json,os,time
from pathlib import Path
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('control',type=Path);p.add_argument('replay',type=Path);p.add_argument('--end',type=int,required=True);p.add_argument('--timeout',type=float,default=180);a=p.parse_args();d=a.control
rows=[]
for line in a.replay.read_text().splitlines():
 if not line.strip() or line.startswith('#'):continue
 values=[int(v,0) for v in line.split()]
 if len(values)!=5:raise SystemExit('Malformed input row')
 rows.append(values)
s=json.loads((d/'status.json').read_text());current=s['vblank']
if not s['paused']:raise SystemExit('Native session must be paused')
while current<a.end:
 matches=[v for v in rows if v[0]<=current<=v[1]]
 if len(matches)!=1:raise SystemExit(f'Replay missing or overlapping at {current}')
 first,last,buttons,x,y=matches[0];end=min(last+1,a.end);seq=s['sequence']+1
 tmp=d/'command.tmp';tmp.write_text(f'{seq} {end} {buttons} {x} {y}\n');os.replace(tmp,d/'command.txt')
 deadline=time.monotonic()+a.timeout
 while time.monotonic()<deadline:
  try:
   n=json.loads((d/'status.json').read_text())
   if n['sequence']==seq and n['paused'] and n['vblank']==end:s=n;break
  except (FileNotFoundError,json.JSONDecodeError):pass
  time.sleep(.05)
 else:raise SystemExit(f'Timeout waiting for native step {seq}/{end}')
 current=s['vblank'];print(json.dumps(s),flush=True)
im=Image.open(d/s['frame']);im.resize((im.width*2,im.height*2),Image.Resampling.NEAREST).save(d/'latest.png')
print(d/'latest.png')
