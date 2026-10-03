"""Verify and consolidate decoded map/UI originals for user-controlled matching."""
import hashlib,json,shutil,struct,collections
from pathlib import Path
from PIL import Image
r=Path(__file__).resolve().parent.parent
source=r/'work/texture-dumps058';target=r/'work/texture-dumps-live/textures';target.mkdir(parents=True,exist_ok=True)
files=[]
for p in sorted((source/'textures').glob('*.png')):
 im=Image.open(p).convert('RGBA');digest=hashlib.sha256(struct.pack('<II',*im.size)+im.tobytes()).hexdigest()
 assert p.stem=='tex-v1-'+digest,p.name
 dst=target/p.name;before=hashlib.sha256(p.read_bytes()).hexdigest()
 if dst.exists():assert hashlib.sha256(dst.read_bytes()).hexdigest()==before
 else:shutil.copy2(p,dst)
 assert hashlib.sha256(dst.read_bytes()).hexdigest()==before
 files.append(dict(id=p.stem,file=p.name,width=im.width,height=im.height,sha256=before))
catalog=json.loads((source/'catalog.json').read_text());by_id=collections.defaultdict(list)
for item in catalog['textures']:by_id[item['id']].append({k:item[k] for k in ['archive','name','offset','mip']})
for f in files:f['source_records']=by_id[f['id']]
out=r/'work/texture-dumps-live/catalog.json';out.write_text(json.dumps(dict(images=files,scope='All retained decoded archive textures verified by original RGBA content IDs; unsupported and dynamic cases are not claimed complete.',archive_failures=catalog['failures']),indent=2)+'\n')
(r/'work/mods-user/textures').mkdir(parents=True,exist_ok=True)
(r/'outputs/DUMPS-090-state.json').write_text(json.dumps(dict(verified_images=len(files),catalog=out.relative_to(r).as_posix(),catalog_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),live_dump_directory=target.relative_to(r).as_posix(),replacement_directory='work/mods-user/textures',source_catalog_sha256=hashlib.sha256((source/'catalog.json').read_bytes()).hexdigest(),policy='Originals are preserved and matching is left to the user. Runtime adds original decoded textures, including VRAM/dynamic/UI identities, before replacement lookup.'),indent=2)+'\n')
print('Verified and staged',len(files),'original texture images')
