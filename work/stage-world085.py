"""Verify and stage a supplied world's diffuse assets and explicit missing effects."""
import argparse,hashlib,json
from pathlib import Path
r=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser();p.add_argument('audit');p.add_argument('manifest');p.add_argument('scale',type=float);a=p.parse_args()
audit=json.loads((r/a.audit).read_text());names=sorted({o['geometry'].lower() for o in audit['objects'] if o.get('model_loaded')})
assert 0<len(names)<=64
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assets={};missing=set()
paths=[]
for name in names:
    model=audit['models'][name];path=r/model['path'];assert sha(path)==model['sha256'];assets[model['path']]=sha(path);paths.append(path)
    for m in model['materials']:
        for image in m['images']:
            if image['exists']:
                path=r/image['path'];assert sha(path)==image['sha256'];assets[image['path']]=sha(path)
            else:missing.add(image['name'])
            if 'option_path' in image:
                path=r/image['option_path'];assert sha(path)==image['option_sha256'];assets[image['option_path']]=sha(path)
manifest=r/a.manifest
manifest.write_text(f'RS_WORLD 1 {a.scale:.15g} {-a.scale:.15g} {-a.scale:.15g} {len(paths)}\n'+'\n'.join(json.dumps(path.as_posix()) for path in paths)+'\n')
report=dict(audit=a.audit,manifest=a.manifest,manifest_sha256=sha(manifest),models=len(paths),coordinate_scale=a.scale,asset_sha256=assets,missing_source_image_references=sorted(missing),loaded_missing_normal_segments=sum(audit['models'][name]['missing_normal_segments'] for name in names),scope='Missing source references include unused material/image slots; they are not necessarily required by visible segments. Loaded missing-normal segment count records actual normal fallback. Unsupported models remain original.')
(r/'outputs'/('WORLD-STAGE-085-'+audit['world'].split('/')[-1].split('.')[0]+'.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(models=len(paths),verified_assets=len(assets),missing_source_image_references=len(missing),loaded_missing_normal_segments=report['loaded_missing_normal_segments']),indent=2))
