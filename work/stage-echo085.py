"""Stage measured Echo Base mapping; keep authored texture data intact."""
import hashlib,json,subprocess,sys
from pathlib import Path
r=Path(__file__).resolve().parent.parent
subprocess.run([sys.executable,str(r/'work/stage-world085.py'),'outputs/CONVERTED-PEB-085.json','work/world-echo085.txt',str(25/27)],check=True)
alignment=json.loads((r/'outputs/WORLD-TRIANGLE-ALIGN-085.json').read_text())[0]
assert alignment['axes']==[0,1,2] and alignment['signs']==[-1,-1,1] and alignment['votes']>200
assert max(abs(v) for x in alignment['precise'] for v in x['fixed_scale_translation'])<.001
manifest=r/'work/world-echo085.txt';lines=manifest.read_text().splitlines();count=lines[0].split()[-1]
lines[0]='RS_WORLD 1 '+' '.join(format(x,'.15g') for x in [-25/27,-25/27,25/27])+' '+count
manifest.write_text('\n'.join(lines)+'\n')
report=r/'outputs/WORLD-STAGE-085-PEB.json';data=json.loads(report.read_text())
data.update(manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),coordinate_scale=[-25/27,-25/27,25/27],coordinate_translation=[0,0,0],alignment_evidence='outputs/WORLD-TRIANGLE-ALIGN-085.json')
report.write_text(json.dumps(data,indent=2)+'\n')
