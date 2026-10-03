"""Review non-name source candidates; scores rank, never approve automatically."""
import json
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parent.parent
bound={f['id'] for f in json.loads((root/'outputs/TEXTURE-PACK-066.json').read_text())['files']}
reviewed={r['game']['id'] for r in json.loads((root/'outputs/SOURCE-066-candidates.json').read_text())}
sources=json.loads((root/'work/texture-matches059/source-index.json').read_text())['images'];rows=[]
for game in json.loads((root/'work/texture-matches060/full-resolution.json').read_text())['matches']:
 if game['id'] in bound or game['id'] in reviewed:continue
 cs=[c for c in game['candidates'] if not c['same_name'] and c['source_width']>=game['width'] and c['source_height']>=game['height'] and c['source_rgb_std']>8]
 if not cs:continue
 c=min(cs,key=lambda c:c['best_rgb_rmse'])
 if not .5<c['best_rgb_rmse']<=25:continue
 rows.append(dict(game=game,candidate=c,source=sources[c['source_index']]))
rows.sort(key=lambda r:r['candidate']['best_rgb_rmse']);rows=rows[:64]
(root/'outputs/SOURCE-067-candidates.json').write_text(json.dumps(rows,indent=2)+'\n')
for start in range(0,len(rows),8):
 sheet=Image.new('RGB',(920,8*172),(35,35,35));draw=ImageDraw.Draw(sheet)
 for j,row in enumerate(rows[start:start+8]):
  y=j*172;g=row['game'];c=row['candidate'];src=row['source'];a=Image.open(root/'work/texture-dumps058/textures'/(g['id']+'.png')).convert('RGB');b=Image.open(root/src['paths'][0]).convert('RGB')
  for im,x in [(a,0),(b,170)]:im.thumbnail((164,164));sheet.paste(im,(x,y))
  draw.text((345,y+5),f"{start+j}: {g['records'][0]['name'].split(chr(92))[-1]}\n=> {Path(src['paths'][0]).name}\n{a.size} -> {src['width']}x{src['height']}\nRMSE {c['best_rgb_rmse']:.2f} swap={c['swap_original_rb']}\nsource index {c['source_index']}",fill='white')
 sheet.save(root/f'outputs/SOURCE-067-review-{start//8}.png')
print('Reviewed candidate sheets:',len(rows))
