#!/usr/bin/env python3
"""Replay recorded controller input into an already running native diagnostic.
Only controller inputs are written. Reaching a frame boundary is not gameplay acceptance.
The observed modern-pad sample is applied one VBlank after the diagnostic pause.
"""
from pathlib import Path
import argparse,json,time
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('control_directory',type=Path)
p.add_argument('gamepad_file',type=Path)
p.add_argument('commands',type=Path)
p.add_argument('gamepad_observations',type=Path)
p.add_argument('--timeout',type=float,default=900)
a=p.parse_args()
if not 0<a.timeout<=7200:p.error('timeout must be positive and at most 7200 seconds')
deadline=time.monotonic()+a.timeout
fields=('connected','lx','ly','rx','ry','lt','rt','buttons')
def status():
 try:return json.loads((a.control_directory/'status.json').read_text())
 except (OSError,json.JSONDecodeError):return None
def publish(temp,target):
 end=min(deadline,time.monotonic()+5)
 while True:
  try:temp.replace(target);return
  except PermissionError:
   if time.monotonic()>=end:raise
   time.sleep(.005)
def wait(frame,sequence=None):
 while time.monotonic()<deadline:
  s=status()
  if s and s['paused'] and s['vblank']==frame and (sequence is None or s['sequence']==sequence):return s
  time.sleep(.07)
 raise RuntimeError('Native diagnostic did not reach the expected paused boundary')
raw=json.loads(a.gamepad_observations.read_text())
if not isinstance(raw,list) or len(raw)>10000:raise ValueError('Invalid raw-controller record count')
samples={}
for row in raw:
 t=int(row['observed_vblank'])-1
 if t<0 or t in samples:raise ValueError('Duplicate or invalid observed pad frame')
 if row['connected'] not in (0,1) or any(not -32768<=row[k]<=32767 for k in ('lx','ly','rx','ry')) or any(not 0<=row[k]<=32767 for k in ('lt','rt')) or not 0<=row['buttons']<=0x7fff:raise ValueError('Invalid gamepad sample')
 samples[t]=row
rows=[]
for line in a.commands.read_text().splitlines():
 if not line.strip() or line.startswith('#'):continue
 v=list(map(int,line.split()))
 if len(v)!=6:raise ValueError('Controller command requires six fields')
 _,start,end,b,x,y=v
 if end==0:break
 if not (0<=start<end and end-start<=36000 and 0<=b<=0x3ffff and 0<=x<=255 and 0<=y<=255):raise ValueError('Invalid controller command')
 if rows and rows[-1][1]!=start:raise ValueError('Controller recording is not contiguous')
 rows.append((start,end,b,x,y))
if not 1<=len(rows)<=10000:raise ValueError('Invalid command count')
a.gamepad_file.parent.mkdir(parents=True,exist_ok=True)
try:pad_sequence=int(a.gamepad_file.read_text().split()[0])
except FileNotFoundError:pad_sequence=0
for start,end,b,x,y in rows:
 s=wait(start)
 if start in samples:
  pad_sequence+=1;o=samples[start];tmp=a.gamepad_file.with_suffix('.next')
  tmp.write_text(str(pad_sequence)+' '+' '.join(str(o[k]) for k in fields)+'\n');publish(tmp,a.gamepad_file)
 sequence=s['sequence']+1;tmp=a.control_directory/'command.next'
 tmp.write_text(f'{sequence} {end} {b} {x} {y}\n');publish(tmp,a.control_directory/'command.txt')
 print(json.dumps(wait(end,sequence)),flush=True)
print('Controller replay reached its recorded endpoint. Inspect the native frames; this is not a gameplay verdict.')
