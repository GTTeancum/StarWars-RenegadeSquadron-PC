"""Stage explicit Geonosis droid LOD folders from verified local packs."""
import hashlib,json,math,shutil,struct
from pathlib import Path
root=Path(__file__).resolve().parent.parent
archive=root/'work/game/disc/PSP_GAME/USRDIR/ENVS/PREQUEL/GEONOSIS.PSP'
b=archive.read_bytes();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert b[:8]==b'Asura   '
def string(data,pos):
    end=data.find(b'\0',pos,min(len(data),pos+513));assert end>=pos
    value=data[pos:end].decode('ascii');assert value and all(32<=ord(c)<=126 for c in value)
    return value,pos+((end-pos+4)&~3)
at=8;links=[];resources={}
while at+16<=len(b):
    tag=b[at:at+4];size,version,flags=struct.unpack_from('<III',b,at+4)
    assert size>=16 and at+size<=len(b)
    chunk=b[at:at+size]
    if tag==b'HSKL':
        base,pos=string(chunk,16);variant,pos=string(chunk,pos)
        if base=='battle_droid':
            assert version==flags==0 and pos+8==len(chunk)
            extras,parameter=struct.unpack_from('<If',chunk,pos)
            assert extras==0 and math.isfinite(parameter)
            links.append(dict(base=base,variant=variant,raw_parameter=parameter,offset=at,chunk_sha256=hashlib.sha256(chunk).hexdigest()))
    if tag==b'RSCF' and len(chunk)>=32:
        kind,subtype,payload_size=struct.unpack_from('<III',chunk,16)
        if kind==0:
            name,pos=string(chunk,28)
            if name in ('battle_droid','L1#battle_droid','L2#battle_droid'):
                assert pos+payload_size==len(chunk) and subtype==5
                key,count,vertices,indices=struct.unpack_from('<4I',chunk,pos)
                assert count==21
                resources[name]=dict(key=key,part_slots=count,vertices=vertices,indices=indices,offset=at,chunk_sha256=hashlib.sha256(chunk).hexdigest())
    at+=size
assert b[at:] in (b'',b'\0'*4)
assert {l['variant'] for l in links}=={'L1#battle_droid','L2#battle_droid'} and len(resources)==3
pack=root/'work/mods-skin053-lods'
assert not pack.exists(),'Use a new output folder instead of overwriting a pack.'
for name in resources:
    source=root/('work/mods-skin046-high-detail' if name=='battle_droid' else 'work/mods-skin040-retarget')/'models/battle_droid'
    assert all((source/n).is_file() for n in ['model.msh','model.bindings','cis_inf_battledroid.tga'])
    dest=pack/'models'/name;dest.mkdir(parents=True)
    for filename in ['model.msh','model.bindings','cis_inf_battledroid.tga']:shutil.copyfile(source/filename,dest/filename)
paths=[Path(__file__),archive]+list(pack.rglob('*'))
report={'scope':'Explicit local LOD pack staged; actual transitions not yet gameplay verified','links':links,'resources':resources,'loader_evidence':{'HSKL_dispatch':'08828304 -> 08826B98','base_metadata_copy':'08826BF8 -> 088179AC','copied_skeleton_fields':[20,28,32,36,40,44,48],'LOD_link_fields':[76,80]},'pack':str(pack),'sha256':{str(p):sha(p) for p in paths if p.is_file()}}
(root/'outputs/LOD-053-discovery.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='sha256'},indent=2))
