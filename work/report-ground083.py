"""Record finished capture evidence without inferring gameplay from exit status."""
import hashlib,json,re,sys
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent.parent
pack=json.loads((root/'outputs/TEXTURE-PACK-074.json').read_text())
old={f['id'] for f in json.loads((root/'outputs/TEXTURE-PACK-072.json').read_text())['files']}
report={}
for name in sys.argv[1:]:
    folder=root/'work/runs'/name
    assert folder.resolve().parent==(root/'work/runs').resolve()
    state=json.loads((folder/'run.json').read_text());assert state['exit_code']==0 and not state['timed_out']
    ids=set(re.findall(r'\[overrides\] texture (tex-v1-\w+) loaded',(folder/'native.log').read_text()))
    loaded=[f for f in pack['files'] if f['id'] in ids];frames=[]
    for kind in ['render-720p','render-720p-fxaa']:
        src=next((folder/'frames'/kind).glob('*.ppm'));im=Image.open(src);assert im.size==(1280,720)
        out=root/'outputs'/f'{name}-{kind}.png';im.save(out)
        frames.append(dict(file=out.relative_to(root).as_posix(),sha256=hashlib.sha256(out.read_bytes()).hexdigest()))
    report[name]=dict(state=state,loaded=loaded,new_loaded=[f for f in loaded if f['id'] not in old],frames=frames,visual_state='Requires frame inspection; exit code alone does not establish gameplay')
    print(name,'loaded',len(loaded),'new',len(report[name]['new_loaded']))
(root/'outputs/TEXTURE-RUNTIME-083.json').write_text(json.dumps(report,indent=2)+'\n')


