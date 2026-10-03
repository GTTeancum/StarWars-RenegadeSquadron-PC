"""Audit full authored world/object/model chains without changing supplied assets."""
import argparse,collections,hashlib,json,os,re,subprocess
from pathlib import Path
r=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('world');p.add_argument('report');a=p.parse_args()
base=r/a.base;world=base/'world1'/(a.world+'.wld');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
env=os.environ.copy();env['PATH']=str(r/'work/windows-sdk/bin')+os.pathsep+env['PATH']
models={}
for path in sorted((base/'msh').glob('*.msh')):
    result=subprocess.run([str(r/'work/build-windows-native/profiles/renegade/renegade_override_asset_audit.exe'),'--model-load',str(path)],env=env,capture_output=True,text=True)
    data=json.loads(result.stdout);assert result.returncode==(0 if data['loaded'] else 1)
    data.update(path=path.relative_to(r).as_posix(),sha256=sha(path),exit_code=result.returncode)
    data['warnings']=result.stderr.splitlines()
    for material in data['materials']:
        material['images']=[]
        for slot,name in enumerate(material.get('textures',[material['texture']])):
            if not name:continue
            original=path.parent/name;chosen=None
            for extension in ['.dds','.tga','.png']:
                candidate=original.with_suffix(extension)
                if candidate.is_file():chosen=candidate;break
            item=dict(slot=slot,name=name,exists=chosen is not None)
            if chosen:item.update(path=chosen.relative_to(r).as_posix(),sha256=sha(chosen))
            option=original.with_name(original.name+'.option')
            if option.is_file():item.update(option_path=option.relative_to(r).as_posix(),option_sha256=sha(option))
            material['images'].append(item)
        original=path.parent/material['texture'];chosen=None
        if material['texture']:
            for extension in ['.dds','.tga','.png']:
                candidate=original.with_suffix(extension)
                if candidate.is_file():chosen=candidate;break
        material['texture_exists']=chosen is not None
        if chosen:material.update(texture_path=chosen.relative_to(r).as_posix(),texture_sha256=sha(chosen))
    models[path.name.lower()]=data
pattern=r'Object\("([^"]+)",\s*"([^"]+)",\s*(-?\d+)\)\s*\{([^}]+)\}'
def objects(path):
    result=[]
    for match in re.finditer(pattern,path.read_text()):
        name,cls,seq,body=match.groups();odf=base/'odf'/(cls+'.odf')
        item=dict(name=name,class_name=cls,sequence=int(seq),odf_exists=odf.is_file())
        for field in ['ChildPosition','ChildRotation']:
            m=re.search(field+r'\(([^)]+)\)',body)
            if m:item[field]=[float(x.strip()) for x in m[1].split(',')]
        if odf.is_file():
            item['odf_sha256']=sha(odf);refs=re.findall(r'GeometryName\s*=\s*"([^"]+)"',odf.read_text(),re.I)
            if refs:
                name=Path(refs[-1]).stem+'.msh';item.update(geometry=name,model_present=name.lower() in models,model_loaded=models.get(name.lower(),{}).get('loaded',False))
        result.append(item)
    return result
base_objects=objects(world)
layers=[dict(file=path.relative_to(r).as_posix(),sha256=sha(path),objects=objects(path)) for path in sorted(world.parent.glob('*.lyr'))]
report=dict(scope='Authored world chain audit; successful loading alone does not prove gameplay rendering.',world=world.relative_to(r).as_posix(),world_sha256=sha(world),objects=base_objects,layers=layers,models=models,summary=dict(world_objects=len(base_objects),local_odf_objects=sum(o['odf_exists'] for o in base_objects),fully_loadable_objects=sum(o.get('model_loaded',False) for o in base_objects),models=len(models),loaded_models=sum(m['loaded'] for m in models.values()),failures=dict(collections.Counter(m['error'] for m in models.values() if not m['loaded']))))
(r/a.report).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['summary'],indent=2))
