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
old = json.loads((root / 'work/texture-catalog102/catalog.json').read_text())
baseline_state=json.loads((root/'outputs/TEXTURES-102-state.json').read_text())
assert sha(root/'work/texture-catalog102/catalog.json')==baseline_state['artifact_sha256']['work/texture-catalog102/catalog.json']
old_ids = {r['id'] for r in old['images']}
old_runtime = {r['id'] for r in old['images'] if r['runtime_observed']}
binary = sha(root / 'work/build-windows-native/bin/RenegadeNative.exe')
assert binary == '924ae90a2ed8141bb418df07203100912bb08176eb987b3a834819a49a68e2ec'
boot = sha(root / 'work/game/disc/PSP_GAME/SYSDIR/BOOT.BIN')
assert boot == 'f4c7a9ef93475fc8017f649346ef79b599649dc47462ec419e9fd373146f8c68'
expected = {'coverage103-gc-entry': 'ENVS/GC.PSP', 'coverage103-campaign-entry': None, 'coverage103-gc-alliance-board-gpu': 'ENVS/GC.PSP', 'coverage103-gc-alliance-phase2-gpu': 'ENVS/GC.PSP', 'coverage103-gc-alliance-phase2-software': 'ENVS/GC.PSP', 'coverage103-gc-empire-board-gpu': 'ENVS/GC.PSP', 'coverage103-gc-tech-menu-gpu': 'ENVS/GC.PSP', 'coverage103-gc-troops-menu-gpu': 'ENVS/GC.PSP', 'coverage103-yavin-campaign-recorded-gpu': 'ENVS/CAMPAIGN/YAVIN_IV.PSP'}
all_ids, files, rows, failed = set(), {}, [], []
for name, archive in expected.items():
    folder = root / 'work/runs' / name
    state = json.loads((folder / 'run.json').read_text())
    assert state['state'] == 'finished', name
    assert state['native_binary_sha256'] == binary and state['boot_sha256'] == boot
    assert sha(folder / 'native/RenegadeNative.exe') == state['native_binary_sha256']
    if 'final-' in name: assert state['native_binary_sha256'] == binary
    env = state['environment']
    assert env['RENEGADE_OUTPUT_RESOLUTION'] == '1280x720' and env['RENEGADE_FXAA'] == '1'
    assert env['PSPRECOMP_WINDOW'] == '0' and env['RENEGADE_OVERRIDE_ROOT'].endswith('work\\mods-textures-source074')
    stop = int(env['PSPRECOMP_STOP_VBLANK'])
    log = (folder / 'native.log').read_text(errors='replace')
    if state['exit_code'] != 0 or state['timed_out']:
        assert name == 'coverage103-yavin-campaign-recorded-gpu', name
        manifest=folder/'textures/textures.jsonl';ids=set();original_files={}
        for line in manifest.read_text().splitlines():
            r=json.loads(line);p=manifest.parent/r['file'];data=p.read_bytes()
            if len(data)<26:data+=bytes(26-len(data))
            im=Image.open(io.BytesIO(data)).convert('RGBA')
            id_='tex-v1-'+hashlib.sha256(struct.pack('<II',*im.size)+im.tobytes()).hexdigest()
            assert id_==r['id'] and im.size==(r['width'],r['height'])
            ids.add(id_);original_files[p.relative_to(root).as_posix()]=sha(p)
        opens=sorted({m[1].replace('\\','/') for line in log.splitlines() if '[io] raw UMD open' in line for m in [re.search(r'[\\/](ENVS[\\/][^"\r\n]+)"',line)] if m})
        artifacts=[folder/'run.json',folder/'native.log',manifest,root/'work'/f'{name}-plan.json',root/'work'/f'{name}-replay.txt',Path(env['PSPRECOMP_CONFIG'])]
        assert sha(folder/'input-replay.txt')==sha(root/'work'/f'{name}-replay.txt')
        failed.append(dict(name=name,exit_code=state['exit_code'],timed_out=state['timed_out'],
                           elapsed_seconds=state['elapsed_seconds'],requested_stop_vblank=stop,
                           actual_opens=opens,stop_lines=state['stop_lines'],original_ids=len(ids),
                           original_file_sha256=original_files,
                           artifact_sha256={p.relative_to(root).as_posix():sha(p) for p in artifacts},
                           acceptance='Failed bounded attempt; no completed final render or mission acceptance inferred.'))
        all_ids.update(ids)
        continue
    assert f'VBlank diagnostic stop at {stop} ' in log
    opens = sorted({m.group(1).replace('\\', '/') for line in log.splitlines()
                    if '[io] raw UMD open' in line
                    for m in [re.search(r'[\\/]((?:ENVS|GUIMENU|GRAPHICS|MISC)[\\/][^"\r\n]+)"', line)] if m})
    if archive:
        assert archive in opens, (name, archive)
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
    gpu_features = {}
    if gpu:
        assert counters['frames'] > 0 and counters['draws'] > 0
        captures = re.findall(r'\[gpu-internal-frame\] ([^\r\n]+)', log)
        assert captures, name
        gpu_features = {k:int(value) if value.isdigit() else value
                        for k,value in re.findall(r'(\w+)=(\S+)', captures[-1])}
        assert gpu_features['vblank'] == stop-1 and gpu_features['resolution'] == '1280x720'
        # These are the backend's reported counters, not proof that every
        # unreported GE feature or primitive is supported or visually correct.
        for key in ['unsupported_blend_draws','unsupported_texture_function_draws','unsupported_partial_color_masks']:
            assert key in gpu_features, (name,key)
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
    artifacts = [folder / 'run.json', folder / 'native.log', manifest,
                 root / 'work' / f'{name}-replay.txt', root / 'work' / f'{name}-plan.json', raw, fxaa,
                 Path(env['PSPRECOMP_CONFIG'])]
    if (folder / 'render-report.jsonl').is_file():
        artifacts.append(folder / 'render-report.jsonl')
    artifacts_sha = {p.relative_to(root).as_posix(): sha(p) for p in artifacts}
    assert sha(folder / 'input-replay.txt') == sha(root / 'work' / f'{name}-replay.txt')
    rows.append(dict(name=name, native_binary_sha256=state['native_binary_sha256'], expected_archive=archive, actual_opens=opens,
                     exit_code=state['exit_code'], timed_out=state['timed_out'],
                     stop_vblank=stop, elapsed_seconds=state['elapsed_seconds'],
                     renderer=env['PSPRECOMP_GE_BACKEND'], backend_counters=counters,
                     gpu_feature_counters=gpu_features,
                     raw_dimensions=list(a.size), fxaa_changed_pixels=int(np.any(np.asarray(a) != np.asarray(b), axis=2).sum()),
                     original_ids=len(ids), ids_not_in_catalog102=sorted(ids-old_ids),
                     ids_not_runtime_observed102=sorted(ids-old_runtime),
                     artifact_sha256=artifacts_sha, original_file_sha256=texture_files))
pack = json.loads((root / 'outputs/TEXTURE-PACK-074.json').read_text())
for row in pack['files']:
    # Exact existing override images remain unchanged from their provenance.
    path = root / row['replacement']
    assert path.resolve().is_relative_to(root / 'work/mods-textures-source074/textures')
    assert sha(path) == row['sha256'], path
report = dict(scope='Bounded normal-controller runs and actual 720p renders; menu probes and legacy campaign replay do not prove modern controls, victory, traversal or ship-flight acceptance.',
              native_binary_sha256=binary, boot_sha256=boot, runs=rows, failed_attempts=failed,
              texture_ids_in_new_runs=len(all_ids), newly_catalogued_ids=sorted(all_ids-old_ids),
              newly_runtime_observed_ids=sorted(all_ids-old_runtime),
              screenshot_sha256=files, pack074_files_unchanged=len(pack['files']),
              baseline_catalog102_sha256=sha(root / 'work/texture-catalog102/catalog.json'),
              skipped='No mip/filter changes, image transforms, new bindings or upscales.',
              timing_scope='GPU is HD throughout; software enables HD near capture. Elapsed times are not comparable performance measurements.')
(root / 'outputs/COVERAGE-103.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['runs','screenshot_sha256','newly_catalogued_ids','newly_runtime_observed_ids']} |
                 {'newly_catalogued_ids':len(all_ids-old_ids), 'newly_runtime_observed_ids':len(all_ids-old_runtime)}, indent=2))
