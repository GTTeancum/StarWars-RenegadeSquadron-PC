"""Rank atlas structure independently of mean color; never install candidates."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parent.parent
sources=json.loads((root/'work/texture-matches059/source-index.json').read_text())['images']
games=json.loads((root/'work/texture-matches060/full-resolution.json').read_text())['matches']
bound={f['id']:f for f in json.loads((root/'outputs/TEXTURE-PACK-068.json').read_text())['files']}
def features(rgb):
    # Equal channel weights make this ranking invariant to an R/B swap. Color
    # agreement must be checked separately; a high score is not permission to recolor.
    gray=rgb.mean(axis=-1)
    terms=[gray-gray.mean(axis=(-2,-1),keepdims=True),np.diff(gray,axis=-1),np.diff(gray,axis=-2)]
    parts=[]
    for term in terms:
        flat=term.reshape(len(term),-1)
        norm=np.sqrt((flat*flat).sum(axis=1,keepdims=True))
        parts.append(flat/np.maximum(norm,1e-6))
    out=np.concatenate(parts,axis=1)
    out=out/np.maximum(np.linalg.norm(out,axis=1,keepdims=True),1e-6)
    out[gray.std(axis=(-2,-1))<1e-4]=0
    return out
cache=root/'work/texture-matches060/source-rgb.npy'
sf=np.load(cache);assert sf.shape==(len(sources),24,24,3)
source_features=features(sf)
game_rgb=[]
for g in games:
    im=Image.open(root/'work/texture-dumps058/textures'/(g['id']+'.png')).convert('RGB').resize((24,24),Image.Resampling.BOX)
    game_rgb.append(np.asarray(im,dtype=np.float32)/255)
gf=features(np.stack(game_rgb));scores=gf@source_features.T
results=[];bound_total=0;recovered=0
for i,g in enumerate(games):
    eligible=np.array([s['width']*g['height']==s['height']*g['width'] and s['width']>=g['width'] and s['height']>=g['height'] for s in sources])
    row=np.where(eligible,scores[i],-np.inf)
    old={c['source_index'] for c in g['candidates']};candidates=[]
    for j in np.argsort(row)[::-1][:8]:
        if not np.isfinite(row[j]):continue
        candidates.append(dict(source_index=int(j),pattern_similarity=float(row[j]),new_to_full_resolution_pass=int(j) not in old,source=sources[j]))
    if g['id'] in bound:
        bound_total+=1
        recovered+=any(c['source']['file_sha256']==bound[g['id']]['sha256'] for c in candidates)
    results.append(dict(id=g['id'],width=g['width'],height=g['height'],records=g['records'],already_bound=g['id'] in bound,candidates=candidates))
report=dict(scope='Pattern candidate ranking only. R/B invariant, so color variants require independent review. Alpha and source quality are not inferred. Sources must have matching aspect and at least original dimensions.',feature_cache_sha256=hashlib.sha256(cache.read_bytes()).hexdigest(),reviewed_binding_retrieval=dict(total=bound_total,source_hash_in_top8=recovered),matches=results)
(root/'outputs/TEXTURE-PATTERNS-069.json').write_text(json.dumps(report,indent=2)+'\n')
novel=[]
for g in results:
    if g['already_bound']:continue
    if g['candidates'] and g['candidates'][0]['new_to_full_resolution_pass'] and g['candidates'][0]['pattern_similarity']>=.75:novel.append(g)
novel.sort(key=lambda g:g['candidates'][0]['pattern_similarity'],reverse=True)
(root/'outputs/TEXTURE-PATTERNS-069-novel.json').write_text(json.dumps(novel,indent=2)+'\n')
print(json.dumps(dict(base_images=len(results),novel_best_over_075=len(novel),**report['reviewed_binding_retrieval'])))
