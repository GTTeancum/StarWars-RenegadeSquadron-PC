"""Reproduce the pattern-candidate contact sheets after low-variance filtering."""
import json
from pathlib import Path
from PIL import Image,ImageDraw
r=Path(__file__).resolve().parent.parent
ledger=json.loads((r/'outputs/TEXTURE-REVIEW-LEDGER-073.json').read_text())
ids={g['id'] for g in ledger['base_images'] if g['status']=='scored_candidates_not_yet_reviewed'}
rows=[g for g in json.loads((r/'outputs/TEXTURE-PATTERNS-069.json').read_text())['matches'] if g['id'] in ids and g['candidates']]
rows.sort(key=lambda g:g['candidates'][0]['pattern_similarity'],reverse=True);rows=rows[:48]
assert rows==json.loads((r/'outputs/SOURCE-074-candidates.json').read_text())
for start in range(0,len(rows),8):
 sheet=Image.new('RGB',(920,8*172),(35,35,35));d=ImageDraw.Draw(sheet)
 for j,g in enumerate(rows[start:start+8]):
  c=g['candidates'][0];s=c['source'];a=Image.open(r/'work/texture-dumps058/textures'/(g['id']+'.png')).convert('RGB');b=Image.open(r/s['paths'][0]).convert('RGB');y=j*172
  for im,x in [(a,0),(b,170)]:im.thumbnail((164,164));sheet.paste(im,(x,y))
  d.text((345,y+4),f"{start+j}: {g['records'][0]['name'].split(chr(92))[-1]}\n=> {Path(s['paths'][0]).name}\npattern {c['pattern_similarity']:.4f}\nsource {c['source_index']}",fill='white')
 sheet.save(r/f'outputs/SOURCE-074-review-{start//8}.png')
