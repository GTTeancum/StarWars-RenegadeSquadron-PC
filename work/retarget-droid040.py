"""Experimental low-detail droid bind mapping; no gameplay claim.

Fit one uniform scale to explicitly named joints after a 180-degree Z rotation.
Write inverse(target bind) * axis/scale corrections and check the production
deformer against the original target rest pose. Source assets stay unchanged.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

root=Path(__file__).resolve().parent.parent
exe=root/'work/build-windows-native/profiles/renegade/renegade_override_asset_audit.exe'
env=os.environ.copy();env['PATH']=str(root/'work/windows-sdk/bin')+os.pathsep+env.get('PATH','')
source=Path('Z:/Modding/SWBF2_Modtools/assets/sides/cis/msh')
target_path=root/'outputs/HSKN-033-battle-droid.json'
target=json.loads(target_path.read_text())
assert target['name']=='battle_droid' and len(target['bones'])==21
metadata=subprocess.run([str(exe),'--skeleton',str(source/'cis_inf_bdroid_low1.msh')],env=env,
                        capture_output=True,text=True,check=True)
scene=json.loads(metadata.stdout);nodes={n['name']:n for n in scene['nodes']}
targets={b['name']:b for b in target['bones']}
names={'bone_pelvis':'Bip01 Pelvis','bone_ribcage':'Bip01 Spine1','bone_head':'Bip01 Head'}
for side in ('l','r'):
    for bone,label in [('thigh','Thigh'),('calf','Calf'),('upperarm','UpperArm'),('forearm','Forearm')]:
        names[f'bone_{side}_{bone}']=f'Bip01 {side.upper()} {label}'
assert {n['name'] for n in scene['nodes'] if n['weighted']}==set(names)

def rotate(q,p):
    x,y,z,w=q;a,b,c=p;t=[2*(y*c-z*b),2*(z*a-x*c),2*(x*b-y*a)]
    return [a+w*t[0]+y*t[2]-z*t[1],b+w*t[1]+z*t[0]-x*t[2],c+w*t[2]+x*t[1]-y*t[0]]

def position(node):
    p=[0.,0.,0.];seen=set()
    while node:
        assert node['name'] not in seen;seen.add(node['name'])
        p=rotate(node['rotation_xyzw'],[p[i]*node['scale'][i] for i in range(3)])
        p=[p[i]+node['translation'][i] for i in range(3)]
        node=nodes[node['parent']] if node['parent'] else None
    return p

def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def dot(a,b):return sum(x*y for x,y in zip(a,b))

pairs=[]
for name,target_name in names.items():
    p=position(nodes[name]);p=[-p[0],-p[1],p[2]]
    pairs.append((name,target_name,p,targets[target_name]['bind_translation']))
scale=sum(dot(p,t) for _,_,p,t in pairs)/sum(dot(p,p) for _,_,p,_ in pairs)
assert math.isfinite(scale) and 0<scale<10

def target_matrix(b):
    columns=b['bind_rotation_columns'];t=b['bind_translation']
    return [columns[0:3]+[0.],columns[3:6]+[0.],columns[6:9]+[0.],list(t)+[1.]]

def correction(b):
    m=target_matrix(b);a,bcol,c=[col[:3] for col in m[:3]]
    bc=cross(bcol,c);det=dot(a,bc);assert abs(det)>1e-12
    # Inverse rotation rows; retain original measured values, do not assume
    # exact orthonormality after guest float arithmetic.
    rows=[[v/det for v in col] for col in (bc,cross(c,a),cross(a,bcol))]
    result=[]
    for j in range(3):result.extend([rows[i][j]*scale*(-1 if j<2 else 1) for i in range(3)]+[0.])
    result.extend([-dot(row,m[3][:3]) for row in rows]+[1.])
    return result

directory=root/'work/mods-skin040-retarget/models/battle_droid';directory.mkdir(parents=True,exist_ok=True)
model=directory/'model.msh';texture=directory/'cis_inf_battledroid.tga'
shutil.copyfile(source/'cis_inf_bdroid_low1.msh',model)
shutil.copyfile(source/'PC/cis_inf_battledroid.tga',texture)
bindings=directory/'model.bindings'
lines=['RS_SKIN_BINDINGS 1',str(len(names))]
for name,target_name,_,_ in pairs:
    b=targets[target_name]
    lines.append(f'{nodes[name]["index"]} {b["slot"]} '+' '.join(format(v,'.9g') for v in correction(b)))
bindings.write_text('\n'.join(lines)+'\n')
pose=directory/'target-rest.pose'
pose.write_text('RS_SKIN_POSE 1\n21\n'+'\n'.join(' '.join(format(v,'.9g') for col in target_matrix(b) for v in col)
    for b in sorted(target['bones'],key=lambda b:b['slot']))+'\n')
run=subprocess.run([str(exe),'--skin-rest-check',str(model),str(bindings),str(pose),format(scale,'.17g')],
                   env=env,capture_output=True,text=True)
negative=subprocess.run([str(exe),'--skin-rest-check',str(model),str(bindings),str(pose),format(scale*2,'.17g')],
                        env=env,capture_output=True,text=True)
assert negative.returncode==1 and json.loads(negative.stdout)['bind_reconstruction_max_error']>0.1
residuals=[dict(source=name,target=target_name,target_slot=targets[target_name]['slot'],
                distance=math.sqrt(sum((p[i]*scale-t[i])**2 for i in range(3)))) for name,target_name,p,t in pairs]
paths=[Path(__file__),exe,target_path,model,texture,bindings,pose]
report=dict(scope='Experimental explicit retarget corrections and rest-pose reconstruction only; not game animation.',
            rotation='180 degrees around Z',uniform_scale=scale,joint_residuals=residuals,
            max_joint_distance=max(r['distance'] for r in residuals),exit_code=run.returncode,stdout=run.stdout,stderr=run.stderr,
            wrong_scale_control=dict(exit_code=negative.returncode,stdout=negative.stdout,stderr=negative.stderr),
            sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
(root/'outputs/RETARGET-040-rest.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
assert run.returncode==0,run.stderr
