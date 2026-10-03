#!/usr/bin/env python3
"""Advance only controller inputs and host time; inspect real native framebuffer at next pause."""
from pathlib import Path
import argparse,json,time,os
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('control');p.add_argument('--frames',type=int,required=True);p.add_argument('--buttons',type=lambda s:int(s,0),default=0);p.add_argument('--x',type=int,default=128);p.add_argument('--y',type=int,default=128);p.add_argument('--timeout',type=float,default=90);p.add_argument('--scale',type=int,choices=range(2,9),default=2);a=p.parse_args();d=Path(a.control)
s=json.loads((d/'status.json').read_text());assert s['paused'],'Native must already be paused';assert 0<=a.frames<=36000 and 0<=a.buttons<=0x3ffff and 0<=a.x<=255 and 0<=a.y<=255
seq=s['sequence']+1;end=s['vblank']+a.frames if a.frames else 0
q=d/'command.tmp';q.write_text(f'{seq} {end} {a.buttons} {a.x} {a.y}\n');os.replace(q,d/'command.txt')
if not end:print('Controller diagnostic stop requested.');raise SystemExit(0)
until=time.monotonic()+a.timeout
while time.monotonic()<until:
 try:
  result=json.loads((d/'status.json').read_text())
  if result['sequence']==seq and result['paused'] and result['vblank']>=end:
   image=d/result['frame'];im=Image.open(image);im.resize((im.width*a.scale,im.height*a.scale),Image.Resampling.NEAREST).save(d/'latest.png');print(json.dumps(result));print(d/'latest.png');break
 except (json.JSONDecodeError,FileNotFoundError):pass
 time.sleep(.1)
else:raise SystemExit('No new paused frame before timeout; inspect native log (not a gameplay pass).')
