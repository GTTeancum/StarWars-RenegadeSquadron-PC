"""Freeze new evidence tools while preserving historical 100 files."""
import re
from pathlib import Path
root=Path(__file__).resolve().parent.parent
for name in ['catalog-textures','audit-runtime-textures','build-texture-browser',
             'test-texture-browser','snapshot-source']:
    ext='.cjs' if name=='test-texture-browser' else '.py'
    s=(root/'work'/f'{name}100{ext}').read_text()
    s=s.replace('texture-catalog100','texture-catalog101').replace('-100','-101').replace('checkpoint 100','checkpoint 101')
    if name=='catalog-textures':
        s=s.replace('TEXTURES-099-state.json','TEXTURES-100-state.json')
        s=s.replace('texture-catalog099','texture-catalog100')
    p=root/'work'/f'{name}101{ext}'
    assert not p.exists(),p
    p.write_text(s)
s=(root/'work/verify-coverage100.py').read_text().replace('COVERAGE-100','COVERAGE-101')
s=s.replace('catalog099','catalog100').replace('observed099','observed100')
s=s.replace("old = json.loads((root / 'work/texture-catalog100/catalog.json').read_text())", """old = json.loads((root / 'work/texture-catalog100/catalog.json').read_text())
baseline_state=json.loads((root/'outputs/TEXTURES-100-state.json').read_text())
assert sha(root/'work/texture-catalog100/catalog.json')==baseline_state['artifact_sha256']['work/texture-catalog100/catalog.json']""")
expected={
    'motion101-hoth-gcw-gpu':'ENVS/CLASSIC/HOTH.PSP',
    'motion101-mygeeto-clone-gpu':'ENVS/PREQUEL/MYGEETO.PSP',
    'motion101-hoth-gcw-software':'ENVS/CLASSIC/HOTH.PSP',
    'motion101-space-kashyyyk-gcw-gpu':'ENVS/CLASSIC/SPACE_KASHYYYK_CIVIL.PSP',
    'motion101-space-kashyyyk-gcw-clear-gpu':'ENVS/CLASSIC/SPACE_KASHYYYK_CIVIL.PSP',
}
s=re.sub(r'^expected = .*$', 'expected = '+repr(expected),s,flags=re.M)
s=s.replace("    gpu = env['PSPRECOMP_GE_BACKEND'] == 'directx12'", '''    assert env['RENEGADE_CONTROLS']=='modern'
    control=root/'work/runs'/('control-'+name)
    plan=json.loads((root/'work'/f'{name}-plan.json').read_text())
    stages=[json.loads(t) for t in (control/'adaptive101.jsonl').read_text().splitlines()]
    extended='-clear-' in name
    assert len(stages)==(9 if extended else 6) and sum(r['frames'] for r in stages)==(645 if extended else 450)
    assert stages[0]['start']==plan['spawn_vblank'] and stages[-1]['end']==stop
    for i,r in enumerate(stages):
        if i:assert stages[i-1]['end']==r['start']
        sample=r['pad_sample'].split()
        assert len(sample)==9 and int(sample[0])==i+2 and sample[1]=='1'
        assert f"sequence={i+2} connected=1 sticks={r['lx']},{r['ly']},{r['rx']},{r['ry']} triggers={r['lt']},{r['rt']}" in log
    commands=[list(map(int,t.split())) for t in (control/'commands.log').read_text().splitlines()]
    assert len(commands)==len(stages)
    for i,(cmd,r) in enumerate(zip(commands,stages)):
        assert cmd==[i+1,r['start'],r['end']+(1 if i==len(stages)-1 else 0),0,128,128]
    actions=[]
    for line in log.splitlines():
        m=re.search(r'\\[action008\\] frame=(\\d+) id=(\\d+) value=([^ ]+) original=([^ ]+) modern=(\\d+) context=([^ ]+)',line)
        if m:actions.append(dict(frame=int(m[1]),id=int(m[2]),value=float(m[3]),original=float(m[4]),modern=int(m[5]),context=m[6]))
    required={'forward':(4,-1),'look-right':(0,1),'forward-fire':(8,1),'strafe-fire':(5,-1),'release-settle':(8,0)}
    if extended:required.update({'backward-retreat':(4,1),'look-left':(0,-1)})
    observations={}
    for label,(action,sign) in required.items():
        stage=next(r for r in stages if r['label']==label)
        hits=[a for a in actions if stage['start']<a['frame']<=stage['end'] and a['id']==action and a['modern']==1 and a['context']=='infantry' and
              (a['value']==0 if sign==0 else a['value']*sign>0.1)]
        assert hits,(name,label,action,'No verified modern infantry input consumption')
        observations[label]=hits
    gpu = env['PSPRECOMP_GE_BACKEND'] == 'directx12' ''')
s=s.replace("    artifacts = [folder / 'run.json'", "    artifacts = [control/'adaptive101.jsonl',control/'commands.log',control/'gamepad.txt',control/'status.json', folder / 'run.json'")
s=s.replace("        artifacts.append(folder / 'render-report.jsonl')", "        artifacts.append(folder / 'render-report.jsonl')\n    artifacts += sorted(control.glob('pause_*.ppm'))\n    native_final=folder/f'frames/frame_{stop-1:06d}.ppm'\n    assert Image.open(native_final).size==(480,272)\n    artifacts.append(native_final)")
s=s.replace("renderer=env['PSPRECOMP_GE_BACKEND'], backend_counters=counters,", "renderer=env['PSPRECOMP_GE_BACKEND'], backend_counters=counters, motion=stages, verified_action_transitions=observations,")
s=s.replace('Bounded normal-controller runs and actual 720p renders; spawn captures are not full matches, traversal or ship-flight acceptance.',
            'Bounded modern dual-stick movement, turning and trigger diagnostics with actual input getter evidence and 720p renders. Limited routes are not full matches, verified enemy kills, first-mission completion or ship-flight acceptance.')
p=root/'work/verify-coverage101.py';assert not p.exists();p.write_text(s)
s=(root/'work/verify-texture-catalog100.py').read_text()
s=s.replace('texture-catalog100','texture-catalog101').replace('SOURCE-099','SOURCE-100')
s=s.replace("assert len(ids) == len(catalog['images']) == catalog['counts']['catalog_unique_ids']", """assert len(ids) == len(catalog['images']) == catalog['counts']['catalog_unique_ids']
coverage=json.loads((root/'outputs/COVERAGE-101.json').read_text())
for run in coverage['runs']:
    name=run['name']
    manifest_name=f'work/runs/{name}/textures/textures.jsonl'
    assert catalog['manifest_sha256'][manifest_name]==sha(root/manifest_name),name
    assert catalog['runs'][name]['successful_terminal'],name
    assert catalog['runs'][name]['state_sha256']==sha(root/f'work/runs/{name}/run.json'),name
    for path in run['original_file_sha256']:
        assert Path(path).stem in ids,name""")
s=s.replace("manifest = json.loads((root / 'outputs/SOURCE-100-manifest.json').read_text())", """manifest = json.loads((root / 'outputs/SOURCE-100-manifest.json').read_text())
prior_receipt=json.loads((root/'outputs/SOURCE-100-receipt.json').read_text())
prior_state=json.loads((root/'outputs/TEXTURES-100-state.json').read_text())
for name in ['outputs/SOURCE-100-manifest.json','outputs/TEXTURES-100-state.json']:
    assert sha(root/name)==prior_receipt['artifact_sha256'][name],name
for name,digest in prior_state['artifact_sha256'].items():
    if name.startswith('outputs/FOG-100-'):
        assert sha(root/name)==digest,name""")
start=s.index('changed_native = ');end=s.index('final_tests=',start)
s=s[:start]+'''changed_native=set()
for name,digest in native_sources.items():
    assert sha(root/name)==digest,name
new_native={p.relative_to(root).as_posix() for p in (root/'work/project/source').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
assert new_native==native_sources.keys(),'Native source inventory changed unexpectedly'
'''+s[end:]
s=s.replace("'outputs/COVERAGE-100.json'","'outputs/COVERAGE-101.json'").replace("'outputs/COVERAGE-100-visual.json'","'outputs/COVERAGE-101-visual.json'")
s=s.replace('MUTABILITY-100','MUTABILITY-101').replace('CATALOG-100','CATALOG-101').replace('COVERAGE-100.md','COVERAGE-101.md').replace('TEXTURE-100-browser','TEXTURE-101-browser').replace('TEXTURES-100-state','TEXTURES-101-state')
s=s.replace(", 'outputs/FOG-100-comparisons.json'",'')
s=s.replace("sorted(changed_native|{new_fog_test})",'sorted(changed_native)')
s=s.replace('Fresh checkpoint 100 native build and all 11 rendering tests passed. Actual software/native/HD and GPU fog pixels verified; paired Hoth/Mygeeto runtime evidence in COVERAGE-100.json.',
            'Native sources and binary rehashed unchanged from verified SOURCE-100. All 11 rendering tests passed in checkpoint 100; not repeated for tool-only 101 changes. Modern movement/fire evidence in COVERAGE-101.json.')
p=root/'work/verify-texture-catalog101.py';assert not p.exists();p.write_text(s)
print('Prepared catalog, motion verification and unchanged native/source checks for 101.')
