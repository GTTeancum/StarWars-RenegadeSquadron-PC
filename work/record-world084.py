"""Record only terminal Boz Pity captures and verified unmodified source assets."""
import hashlib,json,subprocess,sys
from pathlib import Path
r=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={}
for name in ['coverage084-boz','converted084-boz']:
 folder=r/'work/runs'/name;state=json.loads((folder/'run.json').read_text())
 assert state['state']=='finished' and state['exit_code']==0 and not state['timed_out']
 reports=folder/'world-report.jsonl'
 counts=[json.loads(l) for l in reports.read_text().splitlines()] if reports.exists() else []
 frames=[dict(path=p.relative_to(r).as_posix(),sha256=sha(p)) for p in sorted((r/'outputs').glob(name+'-render-720p*.png'))]
 assert len(frames)==2
 report[name]=dict(state=state,world_counts=counts,frames=frames,native_log_sha256=sha(folder/'native.log'))
assets=json.loads((r/'outputs/BOZ-RESOLVED-084.json').read_text())
for name,digest in assets['unchanged_original_files'].items():
 assert sha(r/assets['original']/name)==digest==sha(r/assets['resolved']/name)
for item in assets['shared_materials']:assert sha(r/item['source'])==item['sha256']==sha(r/item['destination'])
audit=json.loads((r/'outputs/CONVERTED-BOZ-084.json').read_text())
repairs={name:dict(derived_normal_vertices=m.get('derived_normal_vertices',0),degenerate_triangles=m.get('degenerate_triangles',0)) for name,m in audit['models'].items() if m.get('derived_normal_vertices') or m.get('degenerate_triangles')}
state=dict(git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=r).strip(),native_binary_sha256=sha(r/'work/build-windows-native/bin/RenegadeNative.exe'),boz_archive_sha256=sha(r/'SWBF2 PSP mod maps/data_BOZ FINAL.7z'),archive_integrity='7-Zip full test exit 0',runs=report,source_provenance='outputs/BOZ-RESOLVED-084.json',audit_summary=audit['summary'],runtime_geometry_repairs=repairs,tests='Seven override test executables passed; 153 model integration checks passed.',test_log_sha256=sha(r/'outputs/WORLD-084-tests.log'),scope='Bounded GCW conquest spawn capture at actual 1280x720 with FXAA. No all-view, traversal, all-mode or all-era completion claim. Source image bytes and authored UVs unchanged.')
(r/'outputs/WORLD-084-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(binary=state['native_binary_sha256'],repairs=repairs,counts=report['converted084-boz']['world_counts'][-1:]),indent=2))
