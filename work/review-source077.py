"""Reproduce review candidates from the remaining full-resolution RGB ranking."""
import json
from pathlib import Path
from PIL import Image,ImageDraw
r=Path(__file__).resolve().parent.parent
ids={g['id'] for g in json.loads((r/'outputs/TEXTURE-REVIEW-LEDGER-075.json').read_text())['base_images'] if g['status']=='scored_candidates_not_yet_reviewed'}
sources=json.loads((r/'work/texture-matches059/source-index.json').read_text())['images']
rows=[g for g in json.loads((r/'work/texture-matches060/full-resolution.json').read_text())['matches'] if g['id'] in ids and g['candidates']]
rows.sort(key=lambda g:g['candidates'][0]['best_rgb_rmse']);rows=rows[:64]
combined=[dict(game=g,candidate=g['candidates'][0],source=sources[g['candidates'][0]['source_index']]) for g in rows]
(r/'outputs/SOURCE-077-combined.json').write_text(json.dumps(combined,indent=2)+'\n')
for start in range(0,len(rows),8):
 sheet=Image.new('RGB',(1000,8*150),(35,35,35));d=ImageDraw.Draw(sheet)
 for j,g in enumerate(rows[start:start+8]):
  y=j*150;a=Image.open(r/'work/texture-dumps058/textures'/(g['id']+'.png')).convert('RGB');a.thumbnail((132,132));sheet.paste(a,(0,y+15));d.text((150,y+20),str(start+j)+': '+g['records'][0]['name'].split(chr(92))[-1][:38],fill='white')
  for k,c in enumerate(g['candidates'][:2]):
   s=sources[c['source_index']];b=Image.open(r/s['paths'][0]).convert('RGB');b.thumbnail((132,132));x=480+260*k;sheet.paste(b,(x,y+15));d.text((x,y),Path(s['paths'][0]).name[:33],fill='white');d.text((150,y+45+20*k),f"candidate {k}: RGB error {c['best_rgb_rmse']:.1f}, swap {c['swap_original_rb']}",fill='white')
 sheet.save(r/f'outputs/SOURCE-077-review-{start//8}.png')
print(len(rows),'remaining RGB candidates')
