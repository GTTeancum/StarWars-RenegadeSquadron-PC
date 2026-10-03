"""Save terminal run evidence and lossless full frames/crops for visual review."""
import hashlib,json,re
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parent.parent
pack=json.loads((root/'outputs/TEXTURE-PACK-065.json').read_text())
report={'runs':{},'comparison_caution':'Same replay and render settings; NPC animation and transient effects can differ. Static stonework crop is not resized.'}
images=[]
for name,label in [('source065-yavin-original','Original textures'),('source065-yavin-gameplay','Supplied source textures')]:
    folder=root/'work/runs'/name
    state=json.loads((folder/'run.json').read_text());assert state['exit_code']==0 and not state['timed_out']
    log=(folder/'native.log').read_text();loaded=set(re.findall(r'\[overrides\] texture (tex-v1-\w+) loaded',log))
    entry=dict(state=state,loaded_bindings=[f for f in pack['files'] if f['id'] in loaded],frames={})
    for kind in ['render-720p','render-720p-fxaa']:
        src=folder/'frames'/kind/'frame_002639.ppm';im=Image.open(src);assert im.size==(1280,720)
        dst=root/'outputs'/f'{name}-{kind}.png';im.save(dst)
        entry['frames'][kind]=dict(file=dst.relative_to(root).as_posix(),sha256=hashlib.sha256(dst.read_bytes()).hexdigest())
        if kind=='render-720p-fxaa':images.append((label,im.copy()))
    report['runs'][name]=entry
crop=(30,245,380,570)
canvas=Image.new('RGB',(700,357),(25,25,25));draw=ImageDraw.Draw(canvas)
for i,(label,im) in enumerate(images):
    draw.text((i*350+10,10),label+' | 720p + FXAA',fill='white');canvas.paste(im.crop(crop),(i*350,32))
dst=root/'outputs/source065-yavin-stonework-comparison.png';canvas.save(dst)
report['comparison']=dict(file=dst.relative_to(root).as_posix(),crop=crop,sha256=hashlib.sha256(dst.read_bytes()).hexdigest())
(root/'outputs/TEXTURE-RUNTIME-065.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({name:dict(exit_code=e['state']['exit_code'],elapsed=e['state']['elapsed_seconds'],loaded_bindings=len(e['loaded_bindings'])) for name,e in report['runs'].items()}))
