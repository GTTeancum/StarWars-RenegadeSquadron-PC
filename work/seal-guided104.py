"""Verify the terminal controller run and preserve a grouped checkpoint."""
import hashlib,io,json,struct,subprocess,sys
from pathlib import Path
from PIL import Image
import numpy as np
root=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
rel=lambda p:p.relative_to(root).as_posix()
out=root/'outputs';run=root/'work/runs/campaign104-modern-guided-gpu'
control=root/'work/runs/control-campaign104-modern-guided-gpu'
state=json.loads((run/'run.json').read_text())
assert state['state']=='finished' and state['exit_code']==0 and not state['timed_out']
assert state['stop_lines']==['[renegade] STOP: Controller diagnostic stop at 4445 pc=0x8ad2c00 work=0']
native=run/'native/RenegadeNative.exe'
assert sha(native)==state['native_binary_sha256']=='507933e4b5ef6a58b3473d3fb636cbd3b0b962c8f57f121bf3444dfd3ec466b4'
assert sha(root/'work/build-windows-native/bin/RenegadeNative.exe')==sha(native)
assert sha(Path(state['command'][1]))==state['boot_sha256']
prior=json.loads((out/'SOURCE-103-manifest.json').read_text())
old={n:d for n,d in prior['source_sha256'].items() if n.startswith('work/project/source/')}
current={rel(p):sha(p) for p in (root/'work/project/source').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
changed=sorted(n for n,d in old.items() if current.get(n)!=d)
added=sorted(current.keys()-old.keys());assert not old.keys()-current.keys()
assert changed==sorted('work/project/source/profiles/renegade/'+n for n in ['host/diagnostic_control.cpp','host/psp_services.cpp','tests/dx12_override.cpp'])
assert added==['work/project/source/profiles/renegade/host/diagnostic_gpu_capture.hpp']
assert '100% tests passed' in (out/'RENDERING-104-build-tests.txt').read_text()
assert 'out of 11' in (out/'RENDERING-104-build-tests.txt').read_text()
records=[json.loads(s) for s in (control/'adaptive104.jsonl').read_text().splitlines()]
commands=[list(map(int,s.split())) for s in (control/'commands.log').read_text().splitlines()]
assert len(records)==len(commands)==33
for i,(record,command) in enumerate(zip(records,commands),1):
 assert record['sequence']==i
 assert command==[i,record['start'],record['until'],record['psp'],record['psp_x'],record['psp_y']]
 if i>1:assert record['start']==records[i-2]['until']
assert records[-1]['until']==0 and records[-1]['start']==4445
captures={};pixel_pairs=0
for p in sorted(control.glob('status_*_vblank_*.json')):
 s=json.loads(p.read_text());assert s['paused'] and s['vblank']==s['until']
 captures[rel(p)]=sha(p)
 assert s['gpu_capture'] and s['gpu_source_vblank']==s['vblank'] and (s['gpu_width'],s['gpu_height'])==(1280,720)
 for field in ['frame','gpu_frame','gpu_fxaa_frame']:
  ppm=control/s[field];png=out/f"campaign104-modern-guided-gpu-{s['sequence']}-{s['vblank']}-{field}.png"
  original=Image.open(ppm);encoded=Image.open(png)
  assert original.size==encoded.size==((480,272) if field=='frame' else (1280,720))
  assert np.array_equal(np.asarray(original),np.asarray(encoded))
  captures[rel(ppm)]=sha(ppm);captures[rel(png)]=sha(png);pixel_pairs+=1
assert pixel_pairs==99 # initial boundary plus32 observed stages
originals={}
for p in sorted((run/'textures').glob('*.tga')):
 data=p.read_bytes();im=Image.open(io.BytesIO(data+bytes(max(0,26-len(data))))).convert('RGBA')
 identity='tex-v1-'+hashlib.sha256(struct.pack('<II',*im.size)+im.tobytes()).hexdigest()
 assert p.stem==identity;originals[rel(p)]=sha(p)
rows=[json.loads(s) for s in (run/'textures/textures.jsonl').read_text().splitlines()]
assert all(rel(run/'textures'/r['file']) in originals and r['id']==Path(r['file']).stem for r in rows)
log=(run/'native.log').read_text(errors='replace')
assert any('raw UMD open' in s and '/ENVS/CAMPAIGN/YAVIN_IV.PSP' in s.replace('\\','/') for s in log.splitlines())
assert all(any('[action008]' in s and ' id='+str(a)+' ' in s and 'modern=1' in s for s in log.splitlines()) for a in [0,4,8,11,16,21])
evidence={rel(p):sha(p) for p in [run/'run.json',run/'native.log',run/'textures/textures.jsonl',native,control/'adaptive104.jsonl',control/'commands.log',root/'work/campaign104-modern-guided-gpu-replay.txt',out/'RENDERING-104-build-tests.txt',out/'RENDERING-104-test-detail.txt',out/'CONTROLS-104-correction.md',out/'VIDEO-104-parity.md']}
report=dict(state='verified terminal progress; incomplete project',run=rel(run),stop_vblank=4445,exit_code=0,timed_out=False,native_binary_sha256=sha(native),native_source_files=len(current),native_source_sha256=current,changed_native=changed,added_native=added,verified_lossless_capture_pairs=pixel_pairs,controller_stages=len(records),original_ids=len(originals),original_file_sha256=originals,capture_sha256=captures,artifact_sha256=evidence,
 findings=['Fresh mission restarted through normal menu at boundary3770. Modern movement, turn, sprint, jump, lock and fire advanced through recon-droid objective; final objective-arrow help visible. No first-mission victory/save/reload/physical controller claim.', 'Earlier101 direction labels corrected: diagnostic SDL negativeLY is forward; positiveLY backward. No production inversion change.', 'CPU movie frame displayed by software but black at same GPU boundary3146/3334. Repair pending, retained reproduction.', 'Actual1280x720 GPU/FXAA,4xMSAA requested, original dumps, software reference retained. No mip/filter changes, matching, new bindings, image transformations or upscales.'],
 catalog_scope='New originals retained in run texture folder with verified content IDs. Frozen catalog103 is not rebuilt in this checkpoint; no newly consolidated coverage/count claim.',
 reproduction='work/build-windows.cmd; work/test-rendering.cmd. work/launch-campaign104.py and recorded adaptive104.jsonl stages, new immutable names required. Source-only snapshot separately excludes game/assets/dependencies/binaries. No fresh-machine build claim.')
(out/'CAMPAIGN-104-verification.json').write_text(json.dumps(report,indent=2)+'\n')
lines=['# Checkpoint104 — current-boundary HD diagnostics and guided tutorial','',*report['findings'],'',f"All11 rendering tests passed after rebuild. Terminal controller stop4445: exit0, no timeout; {pixel_pairs} original/PNG pairs verified pixel-exact, {len(originals)} dumped original texture IDs rehashed. Native source inventory {len(current)} files,3 changed and1 added since frozen103. Native SHA256 `{sha(native)}`.",'', 'Build and controller-stage reproduction, exact hashes, all captures and originals: `CAMPAIGN-104-verification.json`. Full first mission remains unfinished. Texture catalog103 remains frozen; new dumps are retained for manual matching. No missing dependency proven. No commit/push.','', 'Goal is incomplete. Goal API currently reports blocked; authorized work continues under the human instruction. No completed-goal claim.','', '## Rendering changes','', 'Controller pause now happens after GPU finish. Capture metadata identifies the actual source vblank/dimensions; stale/missing GPU frames are not labeled current. ActualDX12 test verifies raw/FXAA capture pixels and malformed-input rejection. Native480x272 reference retained. No guest-state injection.','', '## Reproducibility','',report['reproduction'],'']
for n,d in evidence.items():lines.append(f'- {n}: `{d}`')
(out/'CHECKPOINT-104.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
visual=['# Grouped104 rendering evidence','', 'Actual GPU1280×720 FXAA output; supplied textures retain their orientation/channels. Mip/filter changes skipped. No claim of full mission completion.','']
for seq,frame,title in [(22,3770,'Fresh restarted mission'),(24,3884,'Independent right-stick look'),(25,3919,'Sprint advanced to jump tutorial'),(31,4315,'Modern lock-on'),(32,4445,'Firing advanced past recon droid')]:
 visual += [f'## {title}','',f'![{title}]({root.as_posix()}/outputs/campaign104-modern-guided-gpu-{seq}-{frame}-gpu_fxaa_frame.png)','']
visual += ['## Known movie gap before repair','',f'![Native movie]({root.as_posix()}/outputs/campaign104-modern-guided-gpu-18-3334-frame.png)','',f'![GPU movie]({root.as_posix()}/outputs/campaign104-modern-guided-gpu-18-3334-gpu_frame.png)','']
(out/'RENDERING-104.md').write_text('\n'.join(visual),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k in ['stop_vblank','exit_code','controller_stages','original_ids','native_source_files','verified_lossless_capture_pairs']},indent=2))
