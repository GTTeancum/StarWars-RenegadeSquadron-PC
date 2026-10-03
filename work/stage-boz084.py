"""Stage the measured BOZ coordinate mapping with untouched converted assets."""
import hashlib,json,statistics,subprocess,sys
from pathlib import Path
r=Path(__file__).resolve().parent.parent
subprocess.run([sys.executable,str(r/'work/stage-world084.py'),'outputs/CONVERTED-BOZ-084.json','work/world-boz084.txt',str(5/6)],check=True)
alignment=json.loads((r/'outputs/WORLD-TRIANGLE-ALIGN-084.json').read_text())[0]
assert alignment['axes']==[0,1,2] and alignment['signs']==[-1,-1,1] and alignment['votes']>1000
shifts=[x['fixed_scale_translation'] for x in alignment['precise']]
translation=[statistics.median(x[k] for x in shifts) for k in range(3)]
assert max(max(x[k] for x in shifts)-min(x[k] for x in shifts) for k in range(3))<.0001
manifest=r/'work/world-boz084.txt';lines=manifest.read_text().splitlines();count=lines[0].split()[-1]
lines[0]='RS_WORLD 2 '+' '.join(format(x,'.15g') for x in [-5/6,-5/6,5/6]+translation)+' '+count
manifest.write_text('\n'.join(lines)+'\n')
report=r/'outputs/WORLD-STAGE-084-BOZ.json';data=json.loads(report.read_text())
data.update(manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),coordinate_scale=[-5/6,-5/6,5/6],coordinate_translation=translation,alignment_evidence='outputs/WORLD-TRIANGLE-ALIGN-084.json')
report.write_text(json.dumps(data,indent=2)+'\n')
