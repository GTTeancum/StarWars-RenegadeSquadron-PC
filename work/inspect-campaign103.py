"""Package original campaign outcome frames; never infer victory from exit0."""
import hashlib,json,re
from pathlib import Path
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parent.parent
name='coverage103-yavin-campaign-recorded-gpu';folder=root/'work/runs'/name
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
state=json.loads((folder/'run.json').read_text())
assert state['state']=='finished','Attempt is still live; do not classify it.'
assert state['native_binary_sha256']==sha(folder/'native/RenegadeNative.exe')=='924ae90a2ed8141bb418df07203100912bb08176eb987b3a834819a49a68e2ec'
log=(folder/'native.log').read_text(errors='replace')
opens=sorted({m[1].replace('\\','/') for line in log.splitlines() if '[io] raw UMD open' in line for m in [re.search(r'[\\/](ENVS[\\/][^"\r\n]+)"',line)] if m})
images=[];artifacts=[folder/'run.json',folder/'native.log',root/'work'/f'{name}-plan.json',root/'work'/f'{name}-replay.txt']
for first in [13512,13962,14412]:
 p=folder/f'frames/frame_{first:06d}.ppm'
 if not p.is_file():continue
 im=Image.open(p).convert('RGB');assert im.size==(480,272)
 dest=root/'outputs'/f'{name}-native-{first}.png';im.save(dest)
 assert np.array_equal(np.asarray(im),np.asarray(Image.open(dest)))
 images.append(dest.relative_to(root).as_posix());artifacts += [p,dest]
success=state['exit_code']==0 and not state['timed_out'] and 'VBlank diagnostic stop at 14512 ' in log
r=dict(terminal_verified=True,terminal_success=success,exit_code=state['exit_code'],timed_out=state['timed_out'],
       actual_environment_opens=opens,native_outcome_images=images,
       modern_campaign_acceptance=False,victory_verified=False,save_reload_verified=False,
       finding='Pending actual image inspection. Historical victory and clean exit do not prove this replay completed the mission.',
       metadata_note='Original immutable plan lists first two native captures; actual stride450 also schedules14412. Tool documentation corrected without altering plan/replay/run evidence.',
       artifact_sha256={p.relative_to(root).as_posix():sha(p) for p in artifacts})
dest=root/'outputs/CAMPAIGN-103-outcome.json';assert not dest.exists();dest.write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k!='artifact_sha256'},indent=2))
