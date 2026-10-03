"""Inspect authored world/object/model/material chains using the native loader."""
import collections,hashlib,json,os,re,subprocess
from pathlib import Path
r=Path(__file__).resolve().parent.parent;base=r/'work/map-conversions079/data_PSO/Worlds/PSO';world=base/'world1/PSO.wld'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
env=os.environ.copy();env['PATH']=str(r/'work/windows-sdk/bin')+os.pathsep+env['PATH']
models={}
for p in sorted((base/'MSH').glob('*.msh')):
 result=subprocess.run([str(r/'work/build-windows-native/profiles/renegade/renegade_override_asset_audit.exe'),'--model-load',str(p)],env=env,capture_output=True,text=True)
 data=json.loads(result.stdout);data.update(path=p.relative_to(r).as_posix(),sha256=sha(p),exit_code=result.returncode)
 assert result.returncode==(0 if data['loaded'] else 1)
 for m in data['materials']:
  t=p.parent/m['texture'];m['texture_exists']=t.is_file()
  if t.is_file():m['texture_sha256']=sha(t)
 models[p.name.lower()]=data
objects=[]
pattern=r'Object\("([^"]+)",\s*"([^"]+)",\s*(-?\d+)\)\s*\{([^}]+)\}'
for match in re.finditer(pattern,world.read_text()):
 name,cls,seq,body=match.groups();odf=base/'ODF'/(cls+'.odf');entry=dict(name=name,class_name=cls,sequence=int(seq),odf_exists=odf.is_file())
 for field in ['ChildPosition','ChildRotation']:
  m=re.search(field+r'\(([^)]+)\)',body)
  if m:entry[field]=[float(x.strip()) for x in m[1].split(',')]
 if odf.is_file():
  entry['odf_sha256']=sha(odf);refs=re.findall(r'GeometryName\s*=\s*"([^"]+)"',odf.read_text(),re.I)
  if refs:
   model=Path(refs[-1]).stem+'.msh';entry['geometry']=model;entry['model_present']=model.lower() in models;entry['model_loaded']=models.get(model.lower(),{}).get('loaded',False)
 objects.append(entry)
layers=[dict(file=p.relative_to(r).as_posix(),sha256=sha(p),object_count=len(list(re.finditer(pattern,p.read_text())))) for p in sorted(world.parent.glob('*.lyr'))]
report=dict(scope='Authored map chain audit, not runtime rendering or world placement validation. Missing local ODFs may be common gameplay objects outside the extracted world subtree.',world=world.relative_to(r).as_posix(),world_sha256=sha(world),layers=layers,objects=objects,models=models,summary=dict(world_objects=len(objects),local_odf_objects=sum(x['odf_exists'] for x in objects),fully_loadable_objects=sum(x.get('model_loaded',False) for x in objects),models=len(models),loaded_models=sum(x['loaded'] for x in models.values()),failures=dict(collections.Counter(x['error'] for x in models.values() if not x['loaded']))))
(r/'outputs/CONVERTED-MAP-082.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['summary'],indent=2))

