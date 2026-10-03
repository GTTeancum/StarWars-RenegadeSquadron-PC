"""Classify runtime identities without accepting fuzzy or channel-swapped matches."""
import hashlib,json,io
from collections import defaultdict
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent.parent
def open_image(path):
    data=path.read_bytes()
    # Pillow probes a 26-byte TGA footer even for valid 22-byte 1x1 RGBA files.
    # Pad only its in-memory view; source bytes and content pixels stay intact.
    if path.suffix.lower()=='.tga' and len(data)<26:data+=bytes(26-len(data))
    return Image.open(io.BytesIO(data)).convert('RGBA')
def keys(image):
    image=image.convert('RGBA');dims=image.width.to_bytes(4,'little')+image.height.to_bytes(4,'little')
    return 'tex-v1-'+hashlib.sha256(dims+image.tobytes()).hexdigest(),hashlib.sha256(dims+image.convert('RGB').tobytes()).hexdigest()
catalog=json.loads((root/'work/texture-dumps058/catalog.json').read_text())
records=defaultdict(list)
for rec in catalog['textures']:records[rec['id']].append(rec)
rgb_ids=defaultdict(list)
for identity in records:
    path=root/'work/texture-dumps058/textures'/(identity+'.png');decoded,rgb=keys(open_image(path));assert decoded==identity
    rgb_ids[rgb].append(identity)
standalone=[]
for path in sorted((root/'work/game/disc').rglob('*')):
    if path.suffix.lower()!='.png':continue
    im=open_image(path);identity,rgb=keys(im)
    rec=dict(file=path.relative_to(root).as_posix(),id=identity,width=im.width,height=im.height,
             sha256=hashlib.sha256(path.read_bytes()).hexdigest(),scope='Standalone disc/UI PNG; runtime conversion not assumed')
    standalone.append(rec);rgb_ids[rgb].append(identity);records[identity].append(rec)
pack=json.loads((root/'outputs/TEXTURE-PACK-072.json').read_text());bindings={f['id']:f for f in pack['files']}
observations=defaultdict(list);paths={};runs={}
folders=[root/'work/runs'/name for name in ['textures057-discovery','textures064-echo','textures064-alderaan','textures064-geonosis','source065-yavin-gameplay','source065-yavin-original','source066-alderaan','source066-echo','source067-korriban','source068-coruscant','source068-coruscant-spawn','coverage070-saleucami','coverage070-naboo','coverage070-endor','coverage071-endor','coverage072-ordmantell']]
for folder in folders:
    state=json.loads((folder/'run.json').read_text());assert state['state']=='finished' and state['exit_code']==0 and not state['timed_out']
    runs[folder.name]=state
    for line in (folder/'textures/textures.jsonl').read_text().splitlines():
        row=json.loads(line);identity=row['id'];path=folder/'textures'/row['file']
        if identity not in paths:
            assert keys(open_image(path))[0]==identity;paths[identity]=path
        observations[identity].append(dict(run=folder.name,**row))
classified=[];aliases=[]
for identity,path in sorted(paths.items()):
    im=open_image(path);_,rgb=keys(im);matches=sorted(set(rgb_ids.get(rgb,[])))
    if identity in records:status='exact_archive_or_standalone_rgba'
    elif matches:status='exact_rgb_alpha_variant'
    else:status='unmatched_dynamic_or_unindexed'
    swapped=Image.merge('RGBA',(im.getchannel('B'),im.getchannel('G'),im.getchannel('R'),im.getchannel('A')))
    swap_matches=sorted(set(rgb_ids.get(keys(swapped)[1],[]))) if not matches else []
    eligible=[bindings[i] for i in matches if i in bindings]
    hashes={f['sha256'] for f in eligible}
    alias=None
    if identity not in bindings and len(hashes)==1:
        alias=dict(id=identity,original_rgb_matches=matches,source_binding_ids=[f['id'] for f in eligible],source=eligible[0]['source'],sha256=eligible[0]['sha256'],
                   alpha='original',basis='Exact dimensions and RGB; only alpha differs. Preserve runtime alpha. No fuzzy matching.',
                   runtime_original=path.relative_to(root).as_posix())
        aliases.append(alias)
    classified.append(dict(id=identity,status=status,width=im.width,height=im.height,archive_rgb_matches=matches,
                           swapped_rgb_candidates=swap_matches,replacement_already_bound=identity in bindings,
                           eligible_alias=alias is not None,observations=observations[identity],
                           original_file=path.relative_to(root).as_posix(),original_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
counts={s:sum(t['status']==s for t in classified) for s in sorted({t['status'] for t in classified})}
report=dict(scope='Fourteen completed runs across observed scenarios including menus; not all-map runtime coverage',runs=runs,
            standalone_pngs=standalone,unique_runtime_images=len(classified),counts=counts,
            eligible_exact_rgb_aliases=aliases,textures=classified)
(root/'outputs/TEXTURE-RUNTIME-AUDIT-072.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(runtime_ids=len(classified),counts=counts,eligible_aliases=len(aliases),standalone_pngs=len(standalone)),indent=2))
