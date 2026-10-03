"""Generate model.bindings from explicit named bones, catalog and native MSH metadata.

This is an authoring tool, not a runtime JSON pack manifest or automatic retargeter.
"""
import argparse, hashlib, json, math, os, subprocess
from pathlib import Path

root=Path(__file__).resolve().parent.parent

def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def rotate(q,p):
    x,y,z,w=q; a,b,c=p; t=[2*(y*c-z*b),2*(z*a-x*c),2*(x*b-y*a)]
    return [a+w*t[0]+y*t[2]-z*t[1],b+w*t[1]+z*t[0]-x*t[2],c+w*t[2]+x*t[1]-y*t[0]]

def generate(recipe, output, inspect=False):
    if output.exists(): raise ValueError('Output exists; choose a new directory')
    data=json.loads(recipe.read_text(encoding='utf-8-sig'))
    catalog=json.loads((root/'outputs/MODEL-CATALOG.json').read_text())
    archive=next(a for a in catalog['archives'] if a['archive']==data['archive'])
    rec=next(m for m in archive['models'] if m['name']==data['target_resource'])
    if not rec['skeleton_name']: raise ValueError('No supported target skeleton in this archive')
    target=archive['skeletons'][rec['skeleton_name']]
    targets={b['name']:b for b in target['bones']}
    if len(targets)!=len(target['bones']): raise ValueError('Duplicate target bone names')
    msh=Path(data['source_msh']); msh=msh if msh.is_absolute() else root/msh
    exe=root/'work/build-windows-native/profiles/renegade/renegade_override_asset_audit.exe'
    env=os.environ.copy(); env['PATH']=str(root/'work/windows-sdk/bin')+os.pathsep+env.get('PATH','')
    proc=subprocess.run([str(exe),'--skeleton',str(msh)],capture_output=True,text=True,env=env,check=True)
    scene=json.loads(proc.stdout); nodes={n['name']:n for n in scene['nodes']}
    if len(nodes)!=len(scene['nodes']): raise ValueError('Duplicate source bone names')
    weighted={n['name'] for n in scene['nodes'] if n['weighted']}
    if inspect:
        template=dict(archive=data['archive'],target_resource=data['target_resource'],source_msh=data['source_msh'],axis='REVIEW: identity or rotate-z-180',scale='fit-joints',bone_map={name:None for name in sorted(weighted)})
        lines=['# Bones to match','',f'Target resource: `{rec["name"]}`; skeleton: `{target["name"]}`.','',
               'Fill every null in recipe.json with an exact target bone name. Choose axis alignment after inspecting the models. No matches have been guessed.','',
               '## Weighted source bones','', '| MSH index | Source bone |','| ---: | --- |']
        for n in scene['nodes']:
            if n['weighted']: lines.append(f'| {n["index"]} | `{n["name"]}` |')
        lines+=['','## Target pose slots','', '| Slot | Target bone | Parent slot |','| ---: | --- | ---: |']
        for b in target['bones']: lines.append(f'| {b["slot"]} | `{b["name"]}` | {b["parent"]} |')
        output.mkdir(parents=True)
        for name,obj in [('recipe.json',template),('source-skeleton.json',scene),('target-skeleton.json',target)]:
            (output/name).write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
        (output/'BONES.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        print(f'Bone lists and unfilled recipe written to {output}')
        return
    mapping=data['bone_map']
    if set(mapping)!=weighted:
        raise ValueError(f'Bone map must cover every weighted source bone exactly. Missing: {sorted(weighted-set(mapping))}; extra: {sorted(set(mapping)-weighted)}')
    for name in mapping.values():
        if name not in targets: raise ValueError(f'Unknown target bone: {name}')
    axis=data['axis']
    if axis not in ('identity','rotate-z-180'): raise ValueError('axis must be identity or rotate-z-180')
    signs=[-1,-1,1] if axis=='rotate-z-180' else [1,1,1]
    def position(n):
        p=[0.,0.,0.]; seen=set()
        while n:
            if n['name'] in seen: raise ValueError('Cyclic source hierarchy')
            seen.add(n['name']); p=rotate(n['rotation_xyzw'],[p[i]*n['scale'][i] for i in range(3)])
            p=[p[i]+n['translation'][i] for i in range(3)]
            n=nodes[n['parent']] if n['parent'] else None
        return [p[i]*signs[i] for i in range(3)]
    pairs=[(src,dst,position(nodes[src]),targets[dst]['bind_translation']) for src,dst in mapping.items()]
    if data['scale']=='fit-joints':
        denom=sum(dot(p,p) for _,_,p,_ in pairs)
        if denom<=1e-12: raise ValueError('Cannot fit scale to zero-length source skeleton')
        scale=sum(dot(p,t) for _,_,p,t in pairs)/denom
    else: scale=float(data['scale'])
    if not math.isfinite(scale) or scale<=0: raise ValueError('Scale must be finite and positive')
    lines=['RS_SKIN_BINDINGS 1',str(len(mapping))]; residuals=[]
    for src,dst,p,t in pairs:
        bone=targets[dst]; rot=bone['bind_rotation_columns']; a,b,c=rot[:3],rot[3:6],rot[6:9]
        det=dot(a,cross(b,c))
        if not math.isfinite(det) or abs(det)<1e-12: raise ValueError('Singular target bind matrix')
        inv=[[v/det for v in col] for col in (cross(b,c),cross(c,a),cross(a,b))]
        matrix=[]
        for j in range(3): matrix.extend([inv[i][j]*scale*signs[j] for i in range(3)]+[0.])
        matrix.extend([-dot(row,t) for row in inv]+[1.])
        if not all(math.isfinite(v) for v in matrix): raise ValueError('Nonfinite correction')
        lines.append(f'{nodes[src]["index"]} {bone["slot"]} '+' '.join(format(v,'.9g') for v in matrix))
        residuals.append(dict(source=src,source_index=nodes[src]['index'],target=dst,target_slot=bone['slot'],joint_distance=math.sqrt(sum((p[i]*scale-t[i])**2 for i in range(3)))))
    report=dict(target_resource=rec['name'],skeleton=target['name'],archive=archive['archive'],archive_sha256=archive['sha256'],source_msh=str(msh),source_sha256=hashlib.sha256(msh.read_bytes()).hexdigest(),axis=axis,scale=scale,mapping=residuals,max_joint_distance=max(x['joint_distance'] for x in residuals),scope='Named mapping and rest correction generated; animation, proportions and material compatibility still require validation')
    pose=['RS_SKIN_POSE 1',str(len(target['bones']))]
    for b in target['bones']:
        rot=b['bind_rotation_columns']; m=rot[:3]+[0.]+rot[3:6]+[0.]+rot[6:9]+[0.]+b['bind_translation']+[1.]
        pose.append(' '.join(format(v,'.9g') for v in m))
    output.mkdir(parents=True)
    (output/'model.bindings').write_text('\n'.join(lines)+'\n')
    (output/'target-rest.pose').write_text('\n'.join(pose)+'\n')
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recipe',type=Path); parser.add_argument('output',type=Path)
    parser.add_argument('--inspect',action='store_true',help='Export source/target bone lists and an unfilled named mapping recipe')
    args=parser.parse_args()
    try: generate(args.recipe,args.output,args.inspect)
    except (ValueError, KeyError, StopIteration, subprocess.CalledProcessError) as e: parser.exit(1,f'Cannot generate bindings: {e}\n')
