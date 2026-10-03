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
old = json.loads((root / 'work/texture-catalog097/catalog.json').read_text())
old_ids = {r['id'] for r in old['images']}
old_runtime = {r['id'] for r in old['images'] if r['runtime_observed']}
binary = sha(root / 'work/build-windows-native/bin/RenegadeNative.exe')
assert binary == '572c9e0754a939acbc9e4a76da92ad50e76b11245a173fe53fc99f680d38e164'
boot = sha(root / 'work/game/disc/PSP_GAME/SYSDIR/BOOT.BIN')
assert boot == 'f4c7a9ef93475fc8017f649346ef79b599649dc47462ec419e9fd373146f8c68'
expected = {'coverage098-menu-space-kashyyyk': None, 'coverage098-menu-space-kessel': None, 'coverage098-menu-space-mygeeto': None, 'coverage098-planet-space-kashyyyk': None, 'coverage098-planet-space-kessel': None, 'coverage098-planet-space-mygeeto': None, 'coverage098-menu-naboo-2flag': None, 'coverage098-space-kashyyyk-clone-assault-gpu': 'ENVS/PREQUEL/SPACE_KASHYYYK_CLONE.PSP', 'coverage098-space-kessel-gcw-1flag-gpu': 'ENVS/CLASSIC/SPACE_KESSEL.PSP', 'coverage098-space-mygeeto-clone-assault-gpu': 'ENVS/PREQUEL/SPACE_MYGEETO.PSP', 'coverage098-space-kessel-gcw-1flag-software': 'ENVS/CLASSIC/SPACE_KESSEL.PSP', 'coverage098-sullust-gcw-conquest-gpu': 'ENVS/CLASSIC/SULLUST.PSP', 'coverage098-tatooine-clone-conquest-gpu': 'ENVS/PREQUEL/TATOOINE.PSP', 'coverage098-naboo-clone-2flag-gpu': 'ENVS/PREQUEL/NABOO.PSP'}
all_ids, files, rows = set(), {}, []
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
                     raw_dimensions=list(a.size), fxaa_changed_pixels=int(np.any(np.asarray(a) != np.asarray(b), axis=2).sum()),
                     original_ids=len(ids), ids_not_in_catalog097=sorted(ids-old_ids),
                     ids_not_runtime_observed097=sorted(ids-old_runtime),
                     artifact_sha256=artifacts_sha, original_file_sha256=texture_files))
pack = json.loads((root / 'outputs/TEXTURE-PACK-074.json').read_text())
for row in pack['files']:
    # Exact existing override images remain unchanged from their provenance.
    path = root / row['replacement']
    assert path.resolve().is_relative_to(root / 'work/mods-textures-source074/textures')
    assert sha(path) == row['sha256'], path
report = dict(scope='Bounded normal-controller runs and actual 720p renders; spawn captures are not full matches, traversal or ship-flight acceptance.',
              native_binary_sha256=binary, boot_sha256=boot, runs=rows,
              texture_ids_in_new_runs=len(all_ids), newly_catalogued_ids=sorted(all_ids-old_ids),
              newly_runtime_observed_ids=sorted(all_ids-old_runtime),
              screenshot_sha256=files, pack074_files_unchanged=len(pack['files']),
              baseline_catalog097_sha256=sha(root / 'work/texture-catalog097/catalog.json'),
              skipped='No mip/filter changes, image transforms, new bindings or upscales.',
              timing_scope='GPU is HD throughout; software enables HD near capture. Elapsed times are not comparable performance measurements.')
(root / 'outputs/COVERAGE-098.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['runs','screenshot_sha256','newly_catalogued_ids','newly_runtime_observed_ids']} |
                 {'newly_catalogued_ids':len(all_ids-old_ids), 'newly_runtime_observed_ids':len(all_ids-old_runtime)}, indent=2))
