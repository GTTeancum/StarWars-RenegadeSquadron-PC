"""Stage reviewed supplied RGB with per-identity original-alpha preservation."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent.parent
raw_rows=json.loads((root/'outputs/SOURCE-068-candidates.json').read_text())
rows=[dict(id=r['game']['id'],source=r['source'],records=r['game']['records'],source_index=r['candidate']['source_index']) for r in raw_rows]
sources=json.loads((root/'work/texture-matches059/source-index.json').read_text())['images']
catalog=json.loads((root/'work/texture-dumps058/catalog.json').read_text())['textures']
old=json.loads((root/'outputs/TEXTURE-PACK-067.json').read_text())
accepted={6,7,17,20,25,30,40,59,95}
alternate={}
pack=root/'work/mods-textures-source068'
if pack.exists():raise SystemExit('Existing pack preserved.')
pending={};decisions=[]
for i,row in enumerate(rows):
    source=sources[alternate[i]] if i in alternate else row['source']
    decisions.append(dict(row=i,id=row['id'],accepted=i in accepted,source=source['paths'][0],
        source_index=alternate.get(i,row['source_index']),alpha='original' if i in accepted else None,
        reason='Different-name artwork/layout visually reviewed; supplied source retains more RGB detail. Preserve original alpha.' if i in accepted else
               'Held: uncertain correspondence, deliberate color variant, or source appears softened/coarsened without demonstrated improvement.'))
    if i not in accepted:continue
    src=root/source['paths'][0]
    assert hashlib.sha256(src.read_bytes()).hexdigest()==source['file_sha256']
    keys={(t['archive'],t['offset']) for t in catalog if t['mip']==0 and t['id']==row['id']}
    for t in catalog:
        if (t['archive'],t['offset']) not in keys:continue
        if pending.setdefault(t['id'],source['paths'][0])!=source['paths'][0]:raise RuntimeError('Conflicting mip policy')
env=os.environ.copy();env['PATH']=str(root/'work/windows-sdk/bin')+os.pathsep+env['PATH'];validation=[]
for source in sorted(set(pending.values())):
    src=root/source;im=Image.open(src).convert('RGBA')
    expected='tex-v1-'+hashlib.sha256(im.width.to_bytes(4,'little')+im.height.to_bytes(4,'little')+im.tobytes()).hexdigest()
    result=subprocess.run([str(root/'work/build-windows-native/profiles/renegade/renegade_override_asset_audit.exe'),'--texture',str(src)],env=env,capture_output=True,text=True,check=True)
    decoded=json.loads(result.stdout);assert decoded['decoded_id']==expected
    validation.append(dict(source=source,decoded=decoded,source_alpha_range=im.getchannel('A').getextrema()))
files={f['id']:dict(f) for f in old['files']}
for identity,source in pending.items():
    digest=hashlib.sha256((root/source).read_bytes()).hexdigest()
    if identity in files and files[identity]['sha256']!=digest:raise RuntimeError('Existing binding conflict')
shutil.copytree(root/'work/mods-textures-source067',pack)
for identity,source in pending.items():
    src=root/source;dest=pack/'textures'/(identity+src.suffix.lower());shutil.copyfile(src,dest)
    policy=pack/'textures'/(identity+'.json');policy.write_text('{"alpha":"original"}\n')
    files[identity]=dict(id=identity,source=source,sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
                        alpha='original',policy=policy.relative_to(root).as_posix(),policy_sha256=hashlib.sha256(policy.read_bytes()).hexdigest())
for f in files.values():
    f['replacement']=(pack/'textures'/(f['id']+Path(f['source']).suffix.lower())).relative_to(root).as_posix()
    assert hashlib.sha256((root/f['replacement']).read_bytes()).hexdigest()==f['sha256']
    if 'policy_sha256' in f:
        f['policy']=(pack/'textures'/(f['id']+'.json')).relative_to(root).as_posix()
        assert hashlib.sha256((root/f['policy']).read_bytes()).hexdigest()==f['policy_sha256']
report=dict(scope='Partial source RGB upgrade; original runtime alpha retained only where explicitly configured',
            decisions=decisions,native_validation=validation,files=list(files.values()))
(root/'outputs/TEXTURE-PACK-068.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(accepted_base_ids=len(accepted),alpha_bindings=len(pending),total_bindings=len(files),native_validated_sources=len(validation))))
