"""Reproduce source-candidate review for unbound UI artwork."""
import json
from pathlib import Path
from PIL import Image,ImageDraw
r=Path(__file__).resolve().parent.parent
ledger=json.loads((r/'outputs/TEXTURE-REVIEW-LEDGER-072.json').read_text())
patterns={g['id']:g for g in json.loads((r/'outputs/TEXTURE-PATTERNS-069.json').read_text())['matches']}
full={g['id']:g for g in json.loads((r/'work/texture-matches060/full-resolution.json').read_text())['matches']}
sources=json.loads((r/'work/texture-matches059/source-index.json').read_text())['images']
rows=[]
for g in ledger['base_images']:
 if g['status']!='scored_candidates_not_yet_reviewed' or not any('/gui/' in t['name'].lower().replace(chr(92),'/') for t in g['records']):continue
 candidates=[]
 for c in full.get(g['id'],{}).get('candidates',[])[:2]+patterns.get(g['id'],{}).get('candidates',[])[:2]:
  if c['source_index'] not in [x['source_index'] for x in candidates]:candidates.append(dict(source_index=c['source_index'],source=sources[c['source_index']]))
 rows.append(dict(game=g,candidates=candidates))
(r/'outputs/SOURCE-073-ui-candidates.json').write_text(json.dumps(rows,indent=2)+'\n')
for start in range(0,len(rows),6):
 sheet=Image.new('RGB',(1050,6*180),(35,35,35));d=ImageDraw.Draw(sheet)
 for j,row in enumerate(rows[start:start+6]):
  y=j*180;g=row['game'];paths=[r/'work/texture-dumps058/textures'/(g['id']+'.png')]+[r/c['source']['paths'][0] for c in row['candidates']]
  for k,path in enumerate(paths):
   im=Image.open(path).convert('RGB');im.thumbnail((160,145));sheet.paste(im,(k*205,y+30));d.text((k*205,y+15),path.name[:29] if k else str(start+j)+': '+g['records'][0]['name'].split(chr(92))[-1][:25],fill='white')
 sheet.save(r/f'outputs/SOURCE-073-ui-review-{start//6}.png')
print(len(rows),'UI identities')
