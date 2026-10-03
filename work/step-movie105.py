"""Submit one recorded controller-only stage, observe the same live process."""
import argparse,json,time
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('frames',type=int,help='1..2000, or0 for a normal diagnostic stop')
p.add_argument('--label',required=True);p.add_argument('--connected',type=int,choices=[0,1],default=1)
for k in ['lx','ly','rx','ry','lt','rt','buttons','psp']:
 p.add_argument('--'+k,type=lambda s:int(s,0),default=0)
p.add_argument('--psp-x',type=int,default=128);p.add_argument('--psp-y',type=int,default=128)
a=p.parse_args();assert 0<=a.frames<=2000
assert all(-32768<=getattr(a,k)<=32767 for k in ['lx','ly','rx','ry'])
assert all(0<=getattr(a,k)<=32767 for k in ['lt','rt','buttons']) and 0<=a.psp<=0x3ffff
assert 0<=a.psp_x<=255 and 0<=a.psp_y<=255
name='campaign105-movie-parity-gpu';folder=root/'work/runs'/name;control=folder.parent/('control-'+name)
run=json.loads((folder/'run.json').read_text());assert run['state']=='running'
s=json.loads((control/'status.json').read_text());assert s['paused'],'Observe the existing stage; do not resubmit it.'
def publish(path,text):
 tmp=path.with_suffix('.next');tmp.write_text(text);deadline=time.monotonic()+5
 while True:
  try:tmp.replace(path);return
  except PermissionError:
   if time.monotonic()>deadline:raise
   time.sleep(.01)
sequence=s['sequence']+1;pad=control/'gamepad.txt';pad_seq=int(pad.read_text().split()[0])+1
until=s['vblank']+a.frames if a.frames else 0
record=dict(start=s['vblank'],until=until,sequence=sequence,pad_sequence=pad_seq,**vars(a))
with (control/'adaptive105.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
publish(pad,f'{pad_seq} {a.connected} {a.lx} {a.ly} {a.rx} {a.ry} {a.lt} {a.rt} {a.buttons}\n')
publish(control/'command.txt',f'{sequence} {until} {a.psp} {a.psp_x} {a.psp_y}\n')
print(json.dumps(record),flush=True)
deadline=time.monotonic()+300
while time.monotonic()<deadline:
 run=json.loads((folder/'run.json').read_text())
 if run['state']=='finished':
  assert a.frames==0 and run['exit_code']==0 and not run['timed_out'],run
  print('Native stopped normally; first-mission success is not inferred.');break
 try:
  s=json.loads((control/'status.json').read_text())
  if a.frames and s['paused'] and s['sequence']==sequence and s['vblank']==until:
   (control/f'status_{sequence}_vblank_{until}.json').write_text(json.dumps(s,indent=2)+'\n')
   for field in ['frame','gpu_frame','gpu_fxaa_frame']:
    if not s.get(field):continue
    im=Image.open(control/s[field]);expected=(480,272) if field=='frame' else (1280,720)
    assert im.size==expected,(field,im.size)
    im.save(root/'outputs'/f'{name}-{sequence}-{until}-{field}.png')
   print(json.dumps(s));break
 except (OSError,json.JSONDecodeError):pass
 time.sleep(.1)
else:raise TimeoutError('Input submitted; observation timed out. Poll the same native process/status; do not restart or resubmit.')
