"""Retrieve source filename alternatives independently of image similarity."""
import json,re,difflib
from pathlib import Path
from PIL import Image,ImageDraw
r=Path(__file__).resolve().parent.parent
ledger=json.loads((r/'outputs/TEXTURE-REVIEW-LEDGER-074.json').read_text())
sources=json.loads((r/'work/texture-matches059/source-index.json').read_text())['images']
norm=lambda p:re.sub('[^a-z0-9]','',Path(p.replace(chr(92),'/')).stem.lower())
names=[{norm(p) for p in s['paths']} for s in sources]
rows=[]
for g in ledger['base_images']:
 if g['status']!='scored_candidates_not_yet_reviewed':continue
 n={norm(t['name']) for t in g['records']}
 scores=[]
 for i,s in enumerate(sources):
  score=max(difflib.SequenceMatcher(None,a,b).ratio() for a in n for b in names[i])
  if score>=0.7:scores.append((score,i))
 if scores:
  scores.sort(reverse=True);rows.append(dict(game=g,candidates=[dict(score=v,source_index=i,source=sources[i]) for v,i in scores[:2]]))
rows.sort(key=lambda g:g['candidates'][0]['score'],reverse=True);rows=rows[:36]
(r/'outputs/SOURCE-075-candidates.json').write_text(json.dumps(rows,indent=2)+'\n')
for start in range(0,len(rows),6):
 sheet=Image.new('RGB',(1000,6*176),(35,35,35));d=ImageDraw.Draw(sheet)
 for j,row in enumerate(rows[start:start+6]):
  g=row['game'];y=j*176;a=Image.open(r/'work/texture-dumps058/textures'/(g['id']+'.png')).convert('RGB');a.thumbnail((160,145));sheet.paste(a,(0,y+28));d.text((0,y),str(start+j)+': '+g['records'][0]['name'].split(chr(92))[-1][:30],fill='white')
  for k,c in enumerate(row['candidates']):
   b=Image.open(r/c['source']['paths'][0]).convert('RGB');b.thumbnail((160,145));x=330+k*330;sheet.paste(b,(x,y+28));d.text((x,y),Path(c['source']['paths'][0]).name[:40],fill='white')
 sheet.save(r/f'outputs/SOURCE-075-review-{start//6}.png')
print(len(rows),'name alternatives')
