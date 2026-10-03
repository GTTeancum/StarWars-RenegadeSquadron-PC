"""Reproduce the checkpoint 063 alpha-bearing, named source review sheets."""
import json
from collections import defaultdict
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parent.parent
sources=json.loads((root/'work/texture-matches059/source-index.json').read_text())['images']
catalog=json.loads((root/'work/texture-dumps058/catalog.json').read_text())['textures']
bound={f['id'] for f in json.loads((root/'outputs/TEXTURE-PACK-062.json').read_text())['files']}
names=defaultdict(list);groups={};opaque={}
for i,s in enumerate(sources):
    for name in {Path(p).name.lower() for p in s['paths'] if '/thumbnail/' not in p.lower()}:names[name].append((i,s))
for t in catalog:
    if t['mip']==0 and t['id'] not in bound:groups.setdefault(t['id'],[]).append(t)
rows=[]
for identity,records in groups.items():
    name=records[0]['name'].split('\\')[-1].lower();w,h=records[0]['width'],records[0]['height'];opts=[]
    for i,s in names[name]:
        if s['width']*h!=s['height']*w or s['width']<=w:continue
        if i not in opaque:opaque[i]=Image.open(root/s['paths'][0]).convert('RGBA').getchannel('A').getextrema()==(255,255)
        opts.append((i,s))
    if not opts:continue
    orig=Image.open(root/'work/texture-dumps058/textures'/f'{identity}.png').convert('RGBA')
    i,s=max(opts,key=lambda o:o[1]['width']*o[1]['height'])
    if opaque[i] and orig.getchannel('A').getextrema()==(255,255):continue
    rows.append(dict(id=identity,name=name,source_index=i,source=s,records=records,alternate_source_indices=[o[0] for o in opts]))
rows.sort(key=lambda x:(x['records'][0]['archive'],x['name']))
path=root/'outputs/SOURCE-063-candidates.json'
if path.exists():assert json.loads(path.read_text())==rows,'Existing review differs; do not overwrite historical decisions'
else:path.write_text(json.dumps(rows,indent=2)+'\n')
for page in range((len(rows)+9)//10):
    canvas=Image.new('RGB',(820,1500),(30,30,30));d=ImageDraw.Draw(canvas)
    for k,row in enumerate(rows[page*10:(page+1)*10]):
        y=k*150;orig=Image.open(root/'work/texture-dumps058/textures'/f"{row['id']}.png").convert('RGB')
        src=Image.open(root/row['source']['paths'][0]).convert('RGB')
        canvas.paste(orig.resize((140,140)),(0,y));canvas.paste(src.resize((140,140)),(150,y))
        d.text((300,y+8),f"{page*10+k}: {row['name']}\n{row['records'][0]['archive']}\n{orig.size} -> {src.size}\nAlternatives: {row['alternate_source_indices']}",fill='white')
    canvas.save(root/f'outputs/SOURCE-063-review-{page}.png')
print(f'Verified {len(rows)} reproducible review candidates')
