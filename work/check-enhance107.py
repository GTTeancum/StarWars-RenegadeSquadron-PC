"""Verify completed107 chunks without touching the running job."""
import hashlib,json
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent.parent;work=root/'work/upscale107/batch';sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
plan_path=root/'outputs/UPSCALER-107-plan.json';plan=json.loads(plan_path.read_text());state=json.loads((work/'run.json').read_text());assert state['plan_sha256']==sha(plan_path)
total=0
for chunk in range(state['completed_chunks']):
 folder=work/f'{chunk:03d}';receipt=json.loads((folder/'receipt.json').read_text());rows=[r for r in plan['rows'] if r['chunk']==chunk];assert receipt['exit_code']==0 and set(receipt['file_sha256'])=={r['id'] for r in rows}
 for r in rows:
  p=root/r['neural'];assert sha(p)==receipt['file_sha256'][r['id']] and Image.open(p).size==(r['width']*4,r['height']*4)
 assert sha(folder/'native.log')==receipt['log_sha256'];total+=len(rows)
assert total==state['completed_images'];print(json.dumps(dict(state=state['state'],verified_images=total,total=plan['images'],completed_chunks=state['completed_chunks'],active_chunk=state.get('active_chunk')),indent=2))
