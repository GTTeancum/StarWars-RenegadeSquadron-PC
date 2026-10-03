"""Compare candidate source art at original resolution; keep alpha evidence separate."""
import functools,importlib.util,json
from pathlib import Path
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('matcher',root/'work/match-textures059.py')
matcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(matcher)
sources=json.loads((root/'work/texture-matches059/source-index.json').read_text())['images']
games=json.loads((root/'work/texture-matches060/candidates.json').read_text())['matches']

@functools.lru_cache(maxsize=32)
def source_image(index):return matcher.open_rgba(root/sources[index]['paths'][0])

results=[]
for i,game in enumerate(games):
    original=matcher.open_rgba(root/'work/texture-dumps058/textures'/(game['id']+'.png'))
    a=np.asarray(original,dtype=np.float32)
    candidates=game['rgb_candidates'][:4]+[c for c in game['rgb_candidates'][4:] if c['same_name']][:6]
    compared=[];seen=set()
    for c in candidates:
        key=(c['source_index'],c['swap_original_rb'])
        if key in seen:continue
        seen.add(key);im=source_image(c['source_index']);b=np.asarray(im)
        target=a[:,:,[2,1,0,3]] if c['swap_original_rb'] else a
        samples=[]
        # Resample RGB independently; source alpha can be a gloss mask rather
        # than transparency and must not erase color correspondence evidence.
        for label,method in [('box',Image.Resampling.BOX),('bilinear',Image.Resampling.BILINEAR)]:
            rgb=np.asarray(im.convert('RGB').resize(original.size,method),dtype=np.float32)
            alpha=np.asarray(im.getchannel('A').resize(original.size,method),dtype=np.float32)
            samples.append({'filter':label,'rgb_rmse':float(np.sqrt(np.mean((target[:,:,:3]-rgb)**2))),'alpha_rmse':float(np.sqrt(np.mean((target[:,:,3]-alpha)**2)))})
        best=min(samples,key=lambda s:s['rgb_rmse'])
        compared.append(c|{'full_resolution':samples,'best_rgb_rmse':best['rgb_rmse'],'alpha_rmse_at_best_rgb':best['alpha_rmse'],'original_opaque':bool(np.all(a[:,:,3]==255)),'source_opaque':bool(np.all(b[:,:,3]==255)),'source_rgb_std':float(np.std(b[:,:,:3].astype(np.float32))),'larger_source':im.width>original.width and im.height>original.height})
    compared.sort(key=lambda x:x['best_rgb_rmse'])
    results.append({'id':game['id'],'width':game['width'],'height':game['height'],'records':game['records'],'candidates':compared,'status':'requires review'})
    if i%100==0:print('Full-resolution comparisons',i,flush=True)
report={'scope':'Measurement evidence, not automatic identity approval','matches':results}
(root/'work/texture-matches060/full-resolution.json').write_text(json.dumps(report,indent=2)+'\n')
summary={'textures_compared':len(results),'larger_opaque_best_under_8':sum(c['larger_source'] and c['original_opaque'] and c['source_opaque'] and c['best_rgb_rmse']<8 for g in results for c in g['candidates'][:1]),'best_rgb_under_8':sum(g['candidates'][0]['best_rgb_rmse']<8 for g in results)}
(root/'outputs/TEXTURE-FULL-SCORES-060-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
