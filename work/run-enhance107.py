"""Run immutable ESRGAN chunks for checkpoint107."""
import hashlib,json,os,subprocess,time
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent.parent;work=root/'work/upscale107/batch'
plan_path=root/'outputs/UPSCALER-107-plan.json';plan=json.loads(plan_path.read_text())
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
assert sha(root/plan['tool'])==plan['tool_sha256']
for n,d in plan['model_sha256'].items():assert sha(root/plan['model_folder']/n)==d
state_path=work/'run.json';assert not state_path.exists(),'Existing107 job must be inspected, never overwritten or duplicated'
state=dict(state='running',started_unix=time.time(),wrapper_pid=os.getpid(),plan_sha256=sha(plan_path),completed_chunks=0,completed_images=0,active_chunk=None,child_pid=None,acceptance='ESRGAN intermediates only; final pack/gameplay not accepted.')
def publish():
 p=state_path.with_suffix('.next');p.write_text(json.dumps(state,indent=2)+'\n');p.replace(state_path)
publish()
try:
 for chunk in range(plan['chunks']):
  rows=[r for r in plan['rows'] if r['chunk']==chunk];folder=work/f'{chunk:03d}';assert not any((folder/'neural').iterdir())
  for r in rows:assert sha(root/r['input'])==r['input_sha256'] and sha(root/r['original'])==r['original_sha256'] and sha(root/r['clean'])==r['clean_sha256']
  cmd=[str(root/plan['tool']),'-i',str(folder/'input'),'-o',str(folder/'neural'),'-m',str(root/plan['model_folder']),'-n',plan['model'],'-s','4','-g','0','-t','512','-j','1:1:1','-f','png']
  print(f"Starting chunk {chunk+1}/{plan['chunks']}: {len(rows)} images",flush=True);start=time.time();state['active_chunk']=chunk
  with (folder/'native.log').open('xb') as log:
   child=subprocess.Popen(cmd,cwd=root/'work/upscale-tools/official-20220424',stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW);state['child_pid']=child.pid;publish();code=child.wait(timeout=1800)
  assert code==0
  files={}
  for r in rows:
   p=root/r['neural'];assert Image.open(p).size==(r['width']*4,r['height']*4);files[r['id']]=sha(p)
  assert len(list((folder/'neural').glob('*.png')))==len(rows)
  (folder/'receipt.json').write_text(json.dumps(dict(chunk=chunk,elapsed_seconds=time.time()-start,exit_code=code,command=cmd,file_sha256=files,log_sha256=sha(folder/'native.log')),indent=2)+'\n')
  state['completed_chunks']+=1;state['completed_images']+=len(rows);state['active_chunk']=None;state['child_pid']=None;publish();print(f"Completed {state['completed_images']}/{plan['images']}",flush=True)
 state.update(state='finished',elapsed_seconds=time.time()-state['started_unix']);publish()
except BaseException as e:
 state.update(state='failed',error=repr(e),elapsed_seconds=time.time()-state['started_unix']);publish();raise
