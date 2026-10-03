"""Stage the manually reviewed cross-map source additions and validate decoding."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent.parent
rows=json.loads((root/'outputs/SOURCE-062-candidates.json').read_text())
catalog=json.loads((root/'work/texture-dumps058/catalog.json').read_text())['textures']
old=json.loads((root/'outputs/TEXTURE-PACK-061.json').read_text())
reject={2:'Unrelated human face; original is architectural relief.',7:'Unrelated wall pattern and panel layout.',
        18:'Radar dish UV atlas arrangement differs.',20:'Different snow pattern; identity unsupported.'}
pack=root/'work/mods-textures-source062'
if pack.exists():raise SystemExit('Existing pack preserved.')
pending={};decisions=[]
for i,row in enumerate(rows):
    decisions.append(dict(row=i,id=row['id'],accepted=i not in reject,
                          reason=reject.get(i,'Corresponding atlas islands or surface landmarks; opaque RGB source upgrade.'),
                          channel_operation='none',source=row['source']['paths'][0]))
    if i in reject:continue
    keys={(t['archive'],t['offset']) for t in catalog if t['mip']==0 and t['id']==row['id']}
    for rec in catalog:
        if (rec['archive'],rec['offset']) not in keys:continue
        source=row['source']['paths'][0]
        if pending.setdefault(rec['id'],source)!=source:raise RuntimeError('Ambiguous mip binding')
env=os.environ.copy();env['PATH']=str(root/'work/windows-sdk/bin')+os.pathsep+env['PATH']
native=[]
for source in sorted(set(pending.values())):
    src=root/source;im=Image.open(src).convert('RGBA');assert im.getchannel('A').getextrema()==(255,255)
    expected='tex-v1-'+hashlib.sha256(im.width.to_bytes(4,'little')+im.height.to_bytes(4,'little')+im.tobytes()).hexdigest()
    result=subprocess.run([str(root/'work/build-windows-native/profiles/renegade/renegade_override_asset_audit.exe'),'--texture',str(src)],env=env,capture_output=True,text=True,check=True)
    decoded=json.loads(result.stdout);assert decoded['decoded_id']==expected
    native.append(dict(source=source,decoded=decoded,rgba_agreement=True))
shutil.copytree(root/'work/mods-textures-source061',pack)
files={f['id']:dict(f) for f in old['files']}
for identity,source in pending.items():
    src=root/source;digest=hashlib.sha256(src.read_bytes()).hexdigest()
    if identity in files and files[identity]['sha256']!=digest:raise RuntimeError('Existing binding conflict')
    dest=pack/'textures'/(identity+src.suffix.lower());shutil.copyfile(src,dest)
    files[identity]=dict(id=identity,source=source,sha256=digest)
for f in files.values():
    f['replacement']=(pack/'textures'/(f['id']+Path(f['source']).suffix.lower())).relative_to(root).as_posix()
    assert hashlib.sha256((root/f['replacement']).read_bytes()).hexdigest()==f['sha256']
report=dict(scope='Partial source-first expansion across maps; no all-map runtime claim',decisions=decisions,
            native_validation=native,files=list(files.values()))
(root/'outputs/TEXTURE-PACK-062.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(accepted_base_ids=len(rows)-len(reject),rejected=len(reject),new_bindings=len(pending),total_bindings=len(files),native_validated_sources=len(native))))
