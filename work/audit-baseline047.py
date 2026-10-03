"""Compare no-pack gameplay against the saved pre-gloss control; no equality assumption."""
import hashlib,json,re
from pathlib import Path
root=Path(__file__).resolve().parent.parent
old=root/'work/runs/skin039-control';new=root/'work/runs/skin047-no-overrides'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=json.loads((old/'run.json').read_text());b=json.loads((new/'run.json').read_text())
assert a['exit_code']==b['exit_code']==0 and not b['timed_out'] and b['state']=='finished'
assert a['boot_sha256']==b['boot_sha256']
assert 'RENEGADE_OVERRIDE_ROOT' not in b['environment']
assert any('VBlank diagnostic stop at 2576' in s for s in b['stop_lines'])
for k,v in a['environment'].items():
    if not any(x in k for x in ['DIR','WAV','TRACE']):assert b['environment'][k]==v,(k,v)
log=(new/'native.log').read_text(errors='replace')
assert '[overrides]' not in log
p=old/'frames/frame_002575.ppm';q=new/'frames/frame_002575.ppm'
# P6 frame header is three newline-terminated lines in these native dumps.
def pixels(p):
    header=p.read_bytes().split(b'\n',3);assert header[0]==b'P6' and header[2]==b'255'
    return header[1],header[3]
x,px=pixels(p);y,py=pixels(q);assert x==y and len(px)==len(py)
changed=sum(px[i:i+3]!=py[i:i+3] for i in range(0,len(px),3))
paths=[Path(__file__),new/'run.json',new/'native.log',p,q,new/'submissions.jsonl',new/'transforms.jsonl',root/'work/model024-geonosis-replay.txt']
report={'scope':'One no-override Geonosis deployment replay compared with historical control; dynamic-frame equality not assumed','old_binary':a['native_binary_sha256'],'new_binary':b['native_binary_sha256'],'native_run':b,'pixel_count':len(px)//3,'changed_pixels':changed,'equal_frames':px==py,'sha256':{p.relative_to(root).as_posix():sha(p) for p in paths if p.is_file()}}
(root/'outputs/BASELINE-047-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('native_run','sha256')},indent=2))
