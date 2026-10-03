"""Finish the existing corrected run, then validate Hoth and space sequentially."""
import json, subprocess, sys, time
from pathlib import Path
root=Path(__file__).resolve().parent.parent
def call(args):
 subprocess.run([sys.executable,*args],cwd=root,check=True)
name='textures106-mygeeto-clone-after-ui2-gpu';p=root/'work/runs'/name/'run.json'
deadline=time.monotonic()+1000
while True:
 state=json.loads(p.read_text())
 if state['state']=='finished':
  assert state['exit_code']==0 and not state['timed_out'];break
 assert time.monotonic()<deadline,'Existing run did not finish; do not launch duplicates'
 time.sleep(5)
call(['work/inspect-upscale106.py',name])
for planet,scenario in [('hoth','hoth-gcw'),('space-kashyyyk','space-kashyyyk-gcw')]:
 name=f'textures106-{scenario}-after-ui2-gpu'
 assert not (root/'work/runs'/name).exists(),'Immutable run already exists; inspect it rather than relaunching'
 call(['work/capture-upscale106.py',planet,'--name',name,'--era','gcw','--renderer','gpu','--pack','upscale106-ui2'])
 call(['work/inspect-upscale106.py',name])
call(['work/verify-gameplay106.py'])
print('Three corrected gameplay routes verified',flush=True)
