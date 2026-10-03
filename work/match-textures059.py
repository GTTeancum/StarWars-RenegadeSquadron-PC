"""Rank original-source texture candidates in both RGB orders; do not install guesses."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import collections,hashlib,io,json
from pathlib import Path,PureWindowsPath
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parent.parent
out=root/'work/texture-matches059';out.mkdir(exist_ok=True)

def open_rgba(path):
    # Pillow's TGA footer probe seeks before BOF for valid tiny legacy files.
    b=path.read_bytes()
    if path.suffix.lower()=='.tga' and len(b)<26:b+=b'\0'*(26-len(b))
    return Image.open(io.BytesIO(b)).convert('RGBA')

def features(im):
    a=np.asarray(im.resize((24,24),Image.Resampling.BOX),dtype=np.float32)/255
    # Premultiplied RGB avoids matching unused colors under transparent pixels.
    a[:,:,:3]*=a[:,:,3:4]
    return a

def main():
    intake=json.loads((root/'outputs/TEXTURE-SOURCES-058.json').read_text())
    groups={}
    for archive in intake['archives']:
        folder=Path(archive['archive']).stem
        for item in archive['images']:
            path=root/'work/texture-sources058'/folder/Path(item['path'].replace('\\','/'))
            group=groups.setdefault(item['sha256'],{'file_sha256':item['sha256'],'paths':[]})
            group['paths'].append(path.relative_to(root).as_posix())
    sources=[];source_features=[];failures=[]
    for i,g in enumerate(groups.values()):
        try:
            p=root/g['paths'][0];im=open_rgba(p)
            g.update(width=im.width,height=im.height,rgba_sha256=hashlib.sha256(im.tobytes()).hexdigest())
            sources.append(g);source_features.append(features(im))
        except Exception as e:failures.append({'path':g['paths'][0],'error':str(e)})
        if i%500==0:print(f'Source images inspected: {i}/{len(groups)}',flush=True)
    sf=np.stack(source_features);np.save(out/'source-features.npy',sf)
    (out/'source-index.json').write_text(json.dumps({'images':sources,'failures':failures},indent=2)+'\n')
    catalog=json.loads((root/'work/texture-dumps058/catalog.json').read_text());by_id=collections.defaultdict(list)
    for rec in catalog['textures']:
        if rec['mip']==0:by_id[rec['id']].append(rec)
    game=[];gf=[]
    for identity,recs in sorted(by_id.items()):
        im=open_rgba(root/'work/texture-dumps058/textures'/(identity+'.png'))
        game.append({'id':identity,'width':im.width,'height':im.height,'records':recs});gf.append(features(im))
    gf=np.stack(gf);np.save(out/'game-features.npy',gf)
    # Score both hypotheses; never change original IDs when swapping channels.
    flat=sf.reshape(len(sf),-1);norm=np.sum(flat*flat,axis=1)
    matches=[]
    for i,g in enumerate(game):
        names={PureWindowsPath(x['name']).stem.casefold() for x in g['records']}
        candidates=[]
        for swapped in (False,True):
            f=gf[i][:,:,[2,1,0,3]] if swapped else gf[i]
            f=f.flatten();mse=np.maximum(0,(norm+np.sum(f*f)-2*(flat@f))/len(f))
            # Exclude mismatched aspect ratios; cropping/UV changes need review.
            aspect=np.array([abs(s['width']/s['height']-g['width']/g['height'])<1e-6 for s in sources])
            eligible=np.where(aspect,mse,np.inf)
            for j in np.argsort(eligible)[:8]:
                if not np.isfinite(eligible[j]):continue
                s=sources[j];same_name=any(Path(p).stem.casefold() in names for p in s['paths'])
                candidates.append({'source_index':int(j),'swap_original_rb':swapped,'thumbnail_rmse':float(np.sqrt(eligible[j])),'same_name':same_name,'source_width':s['width'],'source_height':s['height']})
        candidates.sort(key=lambda x:x['thumbnail_rmse'])
        matches.append(g|{'candidates':candidates[:8],'status':'unreviewed'})
        if i%200==0:print(f'Textures ranked: {i}/{len(game)}',flush=True)
    report={'scope':'Candidate ranking only; no matches accepted or pack files written','source_count':len(sources),'source_failures':failures,'base_texture_count':len(game),'matches':matches}
    (out/'candidates.json').write_text(json.dumps(report,indent=2)+'\n')
    hist=collections.Counter('swapped' if m['candidates'][0]['swap_original_rb'] else 'normal' for m in matches)
    summary={'source_count':len(sources),'source_failures':failures,'base_texture_count':len(game),'best_channel_order':dict(hist),'best_rmse_under_0.03':sum(m['candidates'][0]['thumbnail_rmse']<.03 for m in matches),'accepted':0}
    (root/'outputs/TEXTURE-MATCHES-059-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
