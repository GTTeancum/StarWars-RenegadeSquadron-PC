"""Broaden source matching with RGB-only structure and explicit named candidates.

Alpha is evaluated separately so gloss masks do not hide otherwise matching art.
Candidates remain unaccepted until reviewed; no replacements are written.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import collections,importlib.util,json
from pathlib import Path,PureWindowsPath
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('previous',root/'work/match-textures059.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
out=root/'work/texture-matches060';out.mkdir(exist_ok=True)
sources=json.loads((root/'work/texture-matches059/source-index.json').read_text())['images']
games=json.loads((root/'work/texture-matches059/candidates.json').read_text())['matches']
names=collections.defaultdict(set)
for i,s in enumerate(sources):
    for p in s['paths']:names[Path(p).stem.casefold()].add(i)
cache=out/'source-rgb.npy'
if cache.exists():sf=np.load(cache)
else:
    arr=[]
    for i,s in enumerate(sources):
        im=previous.open_rgba(root/s['paths'][0]).convert('RGB').resize((24,24),Image.Resampling.BOX)
        arr.append(np.asarray(im,dtype=np.float32)/255)
        if i%500==0:print('RGB features',i,flush=True)
    sf=np.stack(arr);np.save(cache,sf)
assert sf.shape==(len(sources),24,24,3)
flat=sf.reshape(len(sources),-1);norm=np.sum(flat*flat,axis=1)
results=[]
for i,g in enumerate(games):
    original=previous.open_rgba(root/'work/texture-dumps058/textures'/(g['id']+'.png'))
    gf=np.asarray(original.convert('RGB').resize((24,24),Image.Resampling.BOX),dtype=np.float32)/255
    named=set().union(*(names[PureWindowsPath(rec['name']).stem.casefold()] for rec in g['records']))
    candidates=[]
    for swapped in (False,True):
        f=(gf[:,:,::-1] if swapped else gf).flatten()
        mse=np.maximum(0,(norm+np.sum(f*f)-2*flat@f)/len(f))
        eligible=np.array([s['width']*g['height']==g['width']*s['height'] for s in sources])
        mse=np.where(eligible,mse,np.inf)
        indices=set(np.argsort(mse)[:8])|named|{c['source_index'] for c in g['candidates']}
        for j in indices:
            if not np.isfinite(mse[j]):continue
            s=sources[j]
            candidates.append({'source_index':int(j),'swap_original_rb':swapped,'rgb_thumbnail_rmse':float(np.sqrt(mse[j])),'same_name':j in named,'source_width':s['width'],'source_height':s['height']})
    candidates.sort(key=lambda c:c['rgb_thumbnail_rmse'])
    # Preserve all named alternatives even when their artwork differs substantially.
    retained=candidates[:10]+[c for c in candidates[10:] if c['same_name']]
    results.append({k:v for k,v in g.items() if k!='candidates'}|{'rgb_candidates':retained})
    if i%200==0:print('Refined',i,flush=True)
report={'scope':'RGB-only candidates with independent future alpha validation; no automatic acceptance','matches':results}
(out/'candidates.json').write_text(json.dumps(report,indent=2)+'\n')
summary={'base_textures':len(results),'best_rgb_rmse_under_0.03':sum(g['rgb_candidates'][0]['rgb_thumbnail_rmse']<.03 for g in results),'best_same_name':sum(g['rgb_candidates'][0]['same_name'] for g in results),'named_candidates_retained':sum(any(c['same_name'] for c in g['rgb_candidates']) for g in results)}
(root/'outputs/TEXTURE-MATCHES-060-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
