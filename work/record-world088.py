"""Record terminal Echo Base captures with audited source identities."""
import hashlib,json,subprocess
from pathlib import Path
r=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
runs={}
for name in ['coverage085-echo','converted088-echo']:
 folder=r/'work/runs'/name;state=json.loads((folder/'run.json').read_text())
 assert state['state']=='finished' and state['exit_code']==0 and not state['timed_out']
 counts=folder/'world-report.jsonl'
 frames=[dict(path=p.relative_to(r).as_posix(),sha256=sha(p)) for p in sorted((r/'outputs').glob(name+'-render-720p*.png'))]
 assert len(frames)==2
 runs[name]=dict(state=state,world_counts=[json.loads(l) for l in counts.read_text().splitlines()] if counts.exists() else [],frames=frames,native_log_sha256=sha(folder/'native.log'))
audit=json.loads((r/'outputs/CONVERTED-PEB-088.json').read_text());stage=json.loads((r/'outputs/WORLD-STAGE-088-PEB.json').read_text())
assert all(sha(r/name)==digest for name,digest in stage['asset_sha256'].items())
state=dict(git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip(),native_binary_sha256=sha(r/'work/build-windows-native/bin/RenegadeNative.exe'),asset_audit_binary_sha256=sha(r/'work/build-windows-native/profiles/renegade/renegade_override_asset_audit.exe'),archive_sha256=sha(r/'SWBF2 PSP mod maps/data_PEB FINAL.7z'),archive_integrity='7-Zip full test exit 0',runs=runs,audit_summary=audit['summary'],stage=stage,scope='Bounded GCW conquest spawn. 1280x720 FXAA. No source image or UV operations. Not all-view/traversal/all-mode/all-era proof.')
(r/'outputs/WORLD-088-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(runs['converted088-echo']['world_counts'][-1:],indent=2))
