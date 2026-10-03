"""Record and apply normal controller input to a paused native diagnostic."""
import argparse,json,time
from pathlib import Path
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('frames',type=int)
p.add_argument('--connected',type=int,choices=(0,1),default=1)
p.add_argument('--psp-x',type=int,default=128);p.add_argument('--psp-y',type=int,default=128)
for k in ('lx','ly','rx','ry','lt','rt','buttons','psp'):p.add_argument('--'+k,type=int,default=0)
a=p.parse_args();root=Path(__file__).resolve().parent;c=root/'runs'/('control-'+a.run)
s=json.loads((c/'status.json').read_text());assert s['paused'];assert 0<a.frames<=2000
assert all(-32768<=getattr(a,k)<=32767 for k in ('lx','ly','rx','ry'))
assert 0<=a.lt<=32767 and 0<=a.rt<=32767 and 0<=a.buttons<=32767 and 0<=a.psp<=0x3ffff
assert 0<=a.psp_x<=255 and 0<=a.psp_y<=255
def publish(path,text):
 t=path.with_suffix('.next');t.write_text(text);end=time.monotonic()+5
 while True:
  try:t.replace(path);return
  except PermissionError:
   if time.monotonic()>end:raise
   time.sleep(.01)
pad=root/'runs'/('gamepad-'+a.run+'.txt');ps=int(pad.read_text().split()[0])+1
record=dict(start=s['vblank'],end=s['vblank']+a.frames,sequence=s['sequence']+1,pad_sequence=ps,**vars(a))
with (c/'adaptive011.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
publish(pad,f'{ps} {a.connected} {a.lx} {a.ly} {a.rx} {a.ry} {a.lt} {a.rt} {a.buttons}\n')
publish(c/'command.txt',f"{record['sequence']} {record['end']} {a.psp} {a.psp_x} {a.psp_y}\n")
deadline=time.monotonic()+180
while time.monotonic()<deadline:
 run_state=json.loads((root/'runs'/a.run/'run.json').read_text())
 if run_state.get('exit_code') is not None:raise RuntimeError('Native run is terminal: '+str(run_state['exit_code']))
 try:
  st=json.loads((c/'status.json').read_text())
  if st['paused'] and st['vblank']==record['end']:
   out=root.parent/'outputs'/f"{a.run}-vblank{st['vblank']}.png"
   Image.open(c/st['frame']).save(out);print(json.dumps(st));print(out);break
 except (OSError,json.JSONDecodeError):pass
 time.sleep(.1)
else:raise TimeoutError('Input recorded; native did not reach requested pause')
