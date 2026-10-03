"""Reproduce the pattern-candidate contact sheets after low-variance filtering."""
import json
from pathlib import Path
from PIL import Image,ImageDraw
r=Path(__file__).resolve().parent.parent;rows=json.loads((r/'outputs/SOURCE-072-candidates.json').read_text())
for start in range(0,len(rows),8):
 sheet=Image.new('RGB',(920,8*172),(35,35,35));d=ImageDraw.Draw(sheet)
 for j,g in enumerate(rows[start:start+8]):
  c=g['candidates'][0];s=c['source'];a=Image.open(r/'work/texture-dumps058/textures'/(g['id']+'.png')).convert('RGB');b=Image.open(r/s['paths'][0]).convert('RGB');y=j*172
  for im,x in [(a,0),(b,170)]:im.thumbnail((164,164));sheet.paste(im,(x,y))
  d.text((345,y+4),f"{start+j}: {g['records'][0]['name'].split(chr(92))[-1]}\n=> {Path(s['paths'][0]).name}\npattern {c['pattern_similarity']:.4f}\nsource {c['source_index']}",fill='white')
 sheet.save(r/f'outputs/SOURCE-072-review-{start//8}.png')
