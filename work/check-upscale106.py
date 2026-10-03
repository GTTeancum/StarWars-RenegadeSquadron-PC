"""Verify completed native chunks without disturbing the running job."""
import hashlib,json
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent.parent;work=root/'work/upscale106/batch'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
plan_path=root/'outputs/UPSCALER-106-plan.json';plan=json.loads(plan_path.read_text())
state=json.loads((work/'run.json').read_text());assert state['plan_sha256']==sha(plan_path)
total=0
for chunk in range(state['completed_chunks']):
 folder=work/f'{chunk:03d}';r=json.loads((folder/'receipt.json').read_text());assert r['exit_code']==0 and r['chunk']==chunk
 rows=[v for v in plan['rows'] if v.get('chunk')==chunk];assert set(r['file_sha256'])=={v['id'] for v in rows}
 for row in rows:
  p=root/row['neural'];assert sha(p)==r['file_sha256'][row['id']]
  assert Image.open(p).size==(row['width']*4,row['height']*4)
  assert sha(root/row['original'])==row['original_sha256'] and sha(root/row['input'])==row['input_sha256']
 assert sha(folder/'native.log')==r['log_sha256'];total+=len(rows)
assert total==state['completed_images']
print(json.dumps(dict(state=state['state'],completed_chunks=state['completed_chunks'],verified_intermediate_images=total,total_images=plan['neural_images'],active_child=state.get('child_pid'),scope='No completed final pack or gameplay acceptance yet.'),indent=2))
