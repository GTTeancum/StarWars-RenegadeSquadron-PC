"""Verify bounded menu/gameplay runs, actual captures and original dump identities.

No screenshot resampling, image matching or authored texture modifications.
Visual findings in the Markdown checkpoint are separate from these invariants.
"""
import hashlib, io, json, re, struct
from pathlib import Path
import numpy as np
from PIL import Image

root = Path(__file__).resolve().parent.parent
sha = lambda p: hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
old = json.loads((root / 'work/texture-catalog100/catalog.json').read_text())
baseline_state=json.loads((root/'outputs/TEXTURES-100-state.json').read_text())
assert sha(root/'work/texture-catalog100/catalog.json')==baseline_state['artifact_sha256']['work/texture-catalog100/catalog.json']
old_ids = {r['id'] for r in old['images']}
old_runtime = {r['id'] for r in old['images'] if r['runtime_observed']}
binary = sha(root / 'work/build-windows-native/bin/RenegadeNative.exe')
assert binary == '924ae90a2ed8141bb418df07203100912bb08176eb987b3a834819a49a68e2ec'
boot = sha(root / 'work/game/disc/PSP_GAME/SYSDIR/BOOT.BIN')
assert boot == 'f4c7a9ef93475fc8017f649346ef79b599649dc47462ec419e9fd373146f8c68'
expected = {'motion101-hoth-gcw-gpu': 'ENVS/CLASSIC/HOTH.PSP', 'motion101-mygeeto-clone-gpu': 'ENVS/PREQUEL/MYGEETO.PSP', 'motion101-hoth-gcw-software': 'ENVS/CLASSIC/HOTH.PSP', 'motion101-space-kashyyyk-gcw-gpu': 'ENVS/CLASSIC/SPACE_KASHYYYK_CIVIL.PSP'}
all_ids, files, rows = set(), {}, []
expected['motion101-space-kashyyyk-gcw-clear-gpu']='ENVS/CLASSIC/SPACE_KASHYYYK_CIVIL.PSP'
for name, archive in expected.items():
    folder = root / 'work/runs' / name
    state = json.loads((folder / 'run.json').read_text())
    assert state['state'] == 'finished' and state['exit_code'] == 0 and not state['timed_out'], name
    assert state['native_binary_sha256'] == binary and state['boot_sha256'] == boot
    assert sha(folder / 'native/RenegadeNative.exe') == state['native_binary_sha256']
    if 'final-' in name: assert state['native_binary_sha256'] == binary
    env = state['environment']
    assert env['RENEGADE_OUTPUT_RESOLUTION'] == '1280x720' and env['RENEGADE_FXAA'] == '1'
    assert env['PSPRECOMP_WINDOW'] == '0' and env['RENEGADE_OVERRIDE_ROOT'].endswith('work\\mods-textures-source074')
    stop = int(env['PSPRECOMP_STOP_VBLANK'])
    log = (folder / 'native.log').read_text(errors='replace')
    assert f'VBlank diagnostic stop at {stop} ' in log
    opens = sorted({m.group(1).replace('\\', '/') for line in log.splitlines()
                    if '[io] raw UMD open' in line
                    for m in [re.search(r'[\\/]((?:ENVS|GUIMENU|GRAPHICS|MISC)[\\/][^"\r\n]+)"', line)] if m})
    if archive:
        assert archive in opens, (name, archive)
    assert env['RENEGADE_CONTROLS']=='modern'
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
        m=re.search(r'\[action008\] frame=(\d+) id=(\d+) value=([^ ]+) original=([^ ]+) modern=(\d+) context=([^ ]+)',line)
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
    gpu = env['PSPRECOMP_GE_BACKEND'] == 'directx12' 
    if gpu:
        assert env['RENEGADE_HD_CAPTURE'] == '0'
        assert env['PSPRECOMP_GE_GPU_SKIP_SOFTWARE_RASTER'] == '0'
        raw, fxaa = folder / 'gpu.ppm', folder / 'gpu-fxaa.ppm'
    else:
        raw = folder / f'frames/render-720p/frame_{stop-1:06d}.ppm'
        fxaa = folder / f'frames/render-720p-fxaa/frame_{stop-1:06d}.ppm'
    a, b = Image.open(raw).convert('RGB'), Image.open(fxaa).convert('RGB')
    assert a.size == b.size == (1280, 720), name
    # Actual render pixels, lossless encoding only; never enlarged native frames.
    for suffix, im in [('unfiltered', a), ('fxaa', b)]:
        p = root / 'outputs' / f'{name}-{suffix}.png'
        im.save(p)
        assert np.array_equal(np.asarray(Image.open(p)), np.asarray(im))
        files[p.relative_to(root).as_posix()] = sha(p)
    counters = {}
    result = re.search(r'\[ge-backend-result\] (.*)', log)
    assert result, name
    for k, v in re.findall(r'(\w+)=(\S+)', result.group(1)):
        counters[k] = int(v) if v.isdigit() else v
    assert counters['missing_textures'] == 0
    if gpu:
        assert counters['frames'] > 0 and counters['draws'] > 0
    ids, texture_files = set(), {}
    manifest = folder / 'textures/textures.jsonl'
    for line in manifest.read_text().splitlines():
        r = json.loads(line)
        p = manifest.parent / r['file']
        data = p.read_bytes()
        if len(data) < 26:
            data += bytes(26 - len(data))  # PIL footer probe, in memory only
        im = Image.open(io.BytesIO(data)).convert('RGBA')
        id_ = 'tex-v1-' + hashlib.sha256(struct.pack('<II', *im.size) + im.tobytes()).hexdigest()
        assert id_ == r['id'] and im.size == (r['width'], r['height'])
        ids.add(id_)
        texture_files[p.relative_to(root).as_posix()] = sha(p)
    all_ids.update(ids)
    artifacts = [control/'adaptive101.jsonl',control/'commands.log',control/'gamepad.txt',control/'status.json', folder / 'run.json', folder / 'native.log', manifest,
                 root / 'work' / f'{name}-replay.txt', root / 'work' / f'{name}-plan.json', raw, fxaa,
                 Path(env['PSPRECOMP_CONFIG'])]
    if (folder / 'render-report.jsonl').is_file():
        artifacts.append(folder / 'render-report.jsonl')
    artifacts += sorted(control.glob('pause_*.ppm'))
    native_final=folder/f'frames/frame_{stop-1:06d}.ppm'
    assert Image.open(native_final).size==(480,272)
    artifacts.append(native_final)
    artifacts_sha = {p.relative_to(root).as_posix(): sha(p) for p in artifacts}
    assert sha(folder / 'input-replay.txt') == sha(root / 'work' / f'{name}-replay.txt')
    rows.append(dict(name=name, native_binary_sha256=state['native_binary_sha256'], expected_archive=archive, actual_opens=opens,
                     exit_code=state['exit_code'], timed_out=state['timed_out'],
                     stop_vblank=stop, elapsed_seconds=state['elapsed_seconds'],
                     renderer=env['PSPRECOMP_GE_BACKEND'], backend_counters=counters, motion=stages, verified_action_transitions=observations,
                     raw_dimensions=list(a.size), fxaa_changed_pixels=int(np.any(np.asarray(a) != np.asarray(b), axis=2).sum()),
                     original_ids=len(ids), ids_not_in_catalog100=sorted(ids-old_ids),
                     ids_not_runtime_observed100=sorted(ids-old_runtime),
                     artifact_sha256=artifacts_sha, original_file_sha256=texture_files))
pack = json.loads((root / 'outputs/TEXTURE-PACK-074.json').read_text())
for row in pack['files']:
    # Exact existing override images remain unchanged from their provenance.
    path = root / row['replacement']
    assert path.resolve().is_relative_to(root / 'work/mods-textures-source074/textures')
    assert sha(path) == row['sha256'], path
report = dict(scope='Bounded modern dual-stick movement, turning and trigger diagnostics with actual input getter evidence and 720p renders. Limited routes are not full matches, verified enemy kills, first-mission completion or ship-flight acceptance.',
              native_binary_sha256=binary, boot_sha256=boot, runs=rows,
              texture_ids_in_new_runs=len(all_ids), newly_catalogued_ids=sorted(all_ids-old_ids),
              newly_runtime_observed_ids=sorted(all_ids-old_runtime),
              screenshot_sha256=files, pack074_files_unchanged=len(pack['files']),
              baseline_catalog100_sha256=sha(root / 'work/texture-catalog100/catalog.json'),
              skipped='No mip/filter changes, image transforms, new bindings or upscales.',
              timing_scope='GPU is HD throughout; software enables HD near capture. Elapsed times are not comparable performance measurements.')
(root / 'outputs/COVERAGE-101.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['runs','screenshot_sha256','newly_catalogued_ids','newly_runtime_observed_ids']} |
                 {'newly_catalogued_ids':len(all_ids-old_ids), 'newly_runtime_observed_ids':len(all_ids-old_runtime)}, indent=2))
