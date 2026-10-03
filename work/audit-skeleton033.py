"""Audit HSKN metadata against disc boundaries and earlier live-loader evidence."""
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

root=Path(__file__).resolve().parent.parent
reader_path=root/'work/project/source/profiles/renegade/tools/hskn_skeleton.py'
spec=importlib.util.spec_from_file_location('hskn',reader_path)
hskn=importlib.util.module_from_spec(spec);spec.loader.exec_module(hskn)
catalog=json.loads((root/'outputs/ASURA-023-catalog.json').read_text())
counts=collections.Counter(); rejected=collections.Counter(); target=None
for archive in catalog['archives']:
    # Catalog paths are relative to the extracted disc.
    path=root/'work/game/disc'/archive['file']
    data=path.read_bytes()
    assert hashlib.sha256(data).hexdigest()==archive['sha256']
    for resource in archive['resources']:
        for model in resource['models']:
            raw=data[model['offset']:model['offset']+model['size']]
            counts['examined']+=1
            try: skeleton=hskn.parse_skeleton(raw)
            except ValueError as ex:
                rejected[str(ex)]+=1
                continue
            counts['parsed']+=1
            counts['bones']+=len(skeleton['bones'])
            if model['name']=='battle_droid' and path.name=='GEONOSIS.PSP':
                target=dict(skeleton=skeleton,archive=archive['file'],chunk=model,
                            chunk_sha256=hashlib.sha256(raw).hexdigest())
assert target
live_path=root/'work/runs/model023/models.jsonl'
live=next(r for line in live_path.read_text().splitlines()
          if (r:=json.loads(line))['name']=='battle_droid')
arrays={a['field']:a['words'] for a in live['arrays']}
bones=target['skeleton']['bones']
assert arrays[28][:len(bones)]==[b['parent'] for b in bones]
assert arrays[48][:len(bones)]==[b['slot_id'] for b in bones]
poses=[v for b in bones for v in b['translation']+b['rotation_xyzw']]
words=struct.unpack('<'+str(len(poses))+'I',struct.pack('<'+str(len(poses))+'f',*poses))
assert list(words[:64])==arrays[32][:64]
derived_errors={}
for field,key in ((36,'bind_translation'),(40,'bind_rotation_columns')):
    derived=[v for b in bones for v in b[key]]
    count=min(len(derived),len(arrays[field]))
    observed=struct.unpack('<'+str(count)+'f',struct.pack('<'+str(count)+'I',*arrays[field][:count]))
    maximum=max(abs(a-b) for a,b in zip(derived,observed))
    assert maximum < 0.00001,(field,maximum)
    derived_errors[key]=dict(compared_floats=count,max_absolute_error=maximum)
target['live_verified']={'parents':len(bones),'slot_ids':len(bones),'pose_words':64,
                         'derived_bind_pose':derived_errors,
                         'note':'Earlier diagnostic captured only first 256 bytes of each array'}
msh=json.loads((root/'outputs/MSH-033-battle-droid.json').read_text())
target['msh_comparison']={'weighted_vertices':msh['weighted_vertices'],
    'weighted_bones':[n['name'] for n in msh['nodes'] if n['weighted']],
    'exact_weighted_name_matches':sorted({n['name'] for n in msh['nodes'] if n['weighted']}&{b['name'] for b in bones})}
paths=[reader_path,Path(__file__),live_path,
       root/'outputs/HSKN-033-battle-droid.json',
       root/'outputs/SKELETON-033-tests.log',
       root/'outputs/CHECKPOINT-033-SKELETON-LAYOUT.md',
       root/'work/project/source/profiles/renegade/CMakeLists.txt',
       root/'outputs/MSH-033-battle-droid.json',
       root/'work/project/source/profiles/renegade/tests/hskn_skeleton.py',
       root/'work/project/source/profiles/renegade/tests/override_asset_audit.cpp',
       root/'work/build-windows-native/profiles/renegade/renegade_override_asset_audit.exe',
       Path('Z:/Modding/SWBF2_Modtools/assets/sides/cis/msh/cis_inf_bdroid.msh')]
report=dict(counts=counts,rejected=rejected,battle_droid=target,
            hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
(root/'outputs/SKELETON-033-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'counts':counts,'rejected':rejected,'live_verified':target['live_verified'],
                  'msh_comparison':target['msh_comparison']},indent=2))
