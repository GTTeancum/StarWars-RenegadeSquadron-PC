"""Write final checkpoint and grouped capture report from verified evidence."""
import hashlib, json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
read = lambda name: json.loads((root/name).read_text())
sha = lambda name: hashlib.file_digest((root/name).open('rb'), 'sha256').hexdigest()
coverage = read('outputs/COVERAGE-098.json')
state = read('outputs/TEXTURES-098-state.json')
mutable = read('outputs/TEXTURE-MUTABILITY-098.json')
assert all(r['exit_code'] == 0 and not r['timed_out'] for r in coverage['runs'])
assert len(coverage['runs']) == 14
assert state['native_binary_sha256'] == coverage['native_binary_sha256']
assert len(coverage['newly_catalogued_ids']) == 885
for name, digest in coverage['screenshot_sha256'].items():
    assert sha(name) == digest, name

shots = [
    ('Space Kashyyyk — Clone Wars, Assault', 'space-kashyyyk-clone-assault-gpu',
     'Player, hangar surfaces and ships render. Large nearby objective artwork remains visibly coarse.'),
    ('Space Kessel — Galactic Civil War, 1-Flag CTF', 'space-kessel-gcw-1flag-gpu',
     'Player, ships, capital ship and flag-mode HUD render; the floor remains unusually dark.'),
    ('Space Mygeeto — Clone Wars, Assault', 'space-mygeeto-clone-assault-gpu',
     'Player, hangar surfaces, ships and capital ship render.'),
    ('Sullust — Galactic Civil War, Conquest', 'sullust-gcw-conquest-gpu',
     'World geometry, player and other troops render with the conquest HUD.'),
    ('Tatooine — Clone Wars, Conquest', 'tatooine-clone-conquest-gpu',
     'Player and other droids render in the yellow interior; nearby objective artwork remains coarse.'),
    ('Naboo — Clone Wars, 2-Flag CTF', 'naboo-clone-2flag-gpu',
     'Player, other troops, world geometry and flag-mode HUD render.'),
    ('Space Kessel — paired software reference', 'space-kessel-gcw-1flag-software',
     'The same controller replay also has a dark floor in software. This is not proof of a GPU-only defect or original PSP parity.'),
]
report = [
    '# Rendering captures — checkpoint 098', '',
    'Six actual 1280×720 GPU spawn renders with 4× MSAA and FXAA, plus the paired Kessel software reference. Captured headlessly and encoded losslessly; no resizing or image edits. All use the final checkpoint 097 executable.', '',
    'Fog interpolation and packed vertex alignment repairs remain in place; the unchanged native sources retain the passing 10-test suite from 097. No mipmap/filtering changes were made. The existing source074 texture pack is unchanged; these captures do not claim newly matched upgrades for every visible surface.', '',
    'These are bounded spawn diagnostics, not complete matches, traversal, ship flight or flag captures. The minimap remains contained in the inspected gameplay captures. GPU hardware transform remains disabled for gameplay. Software HD rendering activates near capture, so timings are not a backend performance comparison.', '',
]
for title, suffix, note in shots:
    base = f'outputs/coverage098-{suffix}'
    assert f'{base}-fxaa.png' in coverage['screenshot_sha256']
    absolute = root.as_posix()+'/'+base
    report += [f'## {title}', '', note, '',
               f'![{title}]({absolute}-fxaa.png)', '',
               f'[Unfiltered render]({absolute}-unfiltered.png)', '']
report += ['Per-run executable, BOOT, config, replay, log, original-image and screenshot hashes are recorded in `outputs/COVERAGE-098.json`.', '']
(root/'outputs/RENDERING-098.md').write_text('\n'.join(report), encoding='utf-8')

lines = [
    '# Checkpoint 098 — map, era, mode and framebuffer-texture diagnostics', '',
    'Status: concrete progress; goal remains active/incomplete. Latest user scope is rendering improvements and original dumps for manual matching. Item #2 (mipmap/filtering changes) is skipped. Authored textures retain their existing channels and orientation. No automatic matching or upscaling was added.', '',
    '## Verified changes', '',
    '- Added controller-only menu-stage captures to `work/capture-coverage098.py`. No guest injection or archive substitution.',
    '- Verified planet positions 18 Space Kashyyyk, 19 Space Kessel and 20 Space Mygeeto. Kashyyyk/Kessel mode menus show Assault then 1-Flag CTF; Mygeeto has only Clone Wars.',
    '- The Naboo menu probe named `coverage098-menu-naboo-2flag` requested index 2 but visibly selected Hero CTF. Its name is retained as historical intent, not mode evidence. Verified 2-Flag CTF is index 1 and used that index in gameplay.',
    '- Expanded the manual original catalog and added explicit same-run render-target provenance. Changing frame captures are hidden by default with an optional inclusion checkbox; no originals or replacement filenames are discarded.',
    '- Added a mutable-source audit grouping distinct content IDs observed with identical source metadata within one run. Addresses are diagnostic evidence, not asset names or override keys.',
    '- Updated `Browse-Textures.cmd` and `TEXTURE-MATCHING.md` to catalog 098. Every frozen prior catalog remains preserved.', '',
    '## Runtime evidence', '',
    'All 14 runs completed with exit 0 and no timeout: seven menu probes and seven gameplay/backend captures. Expected gameplay archives were actually opened. GPU captures use true 16:9 1280×720, 4× MSAA and FXAA. CPU reference raster is retained and gameplay hardware transform/culling are off.', '',
    '| Run | Renderer | Stop vblank | Seconds | Actual expected gameplay archive |',
    '| --- | --- | ---: | ---: | --- |',
]
for run in coverage['runs']:
    lines.append(f"| {run['name']} | {run['renderer']} | {run['stop_vblank']} | {run['elapsed_seconds']:.3f} | {run['expected_archive'] or 'Menu probe'} |")
lines += ['',
    'GPU diagnostic counters reported zero missing textures in each gameplay run and existing replacements were uploaded/drawn. Source074 remains partial; draw counts do not prove that the desired replacement covers every visible surface. Its 355 image files were rehashed unchanged. No new binding was accepted.', '',
    'Kessel’s floor is dark in both the GPU and paired software capture. This does not establish a GPU-only fault or original PSP visual parity. Large nearby markers and some materials remain coarse; map appearance is not fully accepted.', '',
    '## Original texture coverage and provenance', '',
    f"Consolidated originals: {state['merged_original_ids']:,} verified content IDs in {state['merged_image_files']:,} PNG/TGA files. New runs encountered 1,162 distinct IDs, including 885 absent from frozen catalog 097 and 969 newly runtime-observed IDs. These are content identities, not counts of named materials.", '',
    'Static inventory remains 136 Asura containers, 99 texture archives, 4,963 texture chunks, 12,391 mip occurrences and 2,377 archived RGBA identities. Runtime catalog now combines 52 manifests and 1,641 encountered IDs. Successful retained runs have opened 23 of 47 ENVS archive paths; this is not 23 distinct maps or complete gameplay coverage.', '',
    '| Provenance category | IDs |', '| --- | ---: |',
]
lines += [f'| {key} | {value} |' for key,value in state['counts']['status_counts'].items()]
lines += ['',
    'Tatooine exposed changing 512×512 unswizzled format-3 RGBA samples at VRAM 0x04000000 and 0x04088000. Representative originals were inspected: their upper region contains the rendered scene with differing actors/markers, and their lower region contains neighboring/stale VRAM content. Native frame output explicitly identifies 0x04088000; same-run render reports identify canonical target zero. Classification requires the actual VRAM region, same-run observed canonical target, format 3, unswizzled 512×512 and stride 512. No archived resource names or complete per-draw write histories are inferred.', '',
    f"Mutable-source audit: {mutable['case_count']} source-configuration cases, {mutable['member_ids']} member IDs, including {mutable['render_target_ids_in_cases']} render-target IDs and {mutable['unresolved_origin_ids_in_cases']} origin-unresolved IDs. Cases are not distinct assets; equal addresses across runs do not prove continuity. Full dynamic-texture coverage remains incomplete.", '',
    'Runtime formats 3, 4, 5 and 7 have concrete original dump evidence. Static archives contain the previously decoded formats 4/5. No unsupported static texture headers, uncatalogued texture archives, runtime identity errors or pack errors were reported.', '',
    'Original RGBA identities were verified from little-endian width/height plus decoded RGBA bytes, and all original file hashes checked. The inherited 095 conversion intake has 13,820 images from 12 archives; its frozen source-index files are preserved byte-for-byte. Those source image payloads were not all re-audited again in 098.', '',
    '## Validation and reproducible state', '',
    f"Every one of the {state['unchanged_native_source_files']} source files recorded under `work/project/source/` in SOURCE-097 was rehashed unchanged, as was the final native executable. No native edit or rebuild occurred in 098. The 097 final rendering suite passed all 10 tests, including actual GPU fog-boundary pixels and repaired packed input. Original red/failing diagnostic logs remain preserved.", '',
    'New checks: `verify-coverage098.py` verified terminal states, actual archive opens, isolated executables, BOOT, config/replay/log identities, original image identities and lossless 1280×720 captures. `catalog-textures098.py` verified static/runtime originals and error queues. `audit-runtime-textures098.py` verified source manifests. `test-texture-browser098.cjs` passed map/query/runtime/pagination/filename/provenance and render-target inclusion checks with a code-level DOM stand-in; this is not browser visual QA. `verify-texture-catalog098.py` checked all consolidated original files, evidence hashes and unchanged native state.', '',
    'Existing build: Windows x64 Release, CMake/Ninja, MSVC 14.44.35207, Windows SDK 10.0.26100.0 and retained `work/windows-sdk`. Rebuild with `work/build-windows.cmd`; native rendering checks with `work/test-rendering.cmd`. No dependency request was needed. Source snapshot records CMakeCache, build scripts and existing compiler/dependency file hashes, but is not a fresh-machine build test.', '',
    'To reproduce a route, use the bundled Python with Pillow to run `work/capture-coverage098.py` with the planet, era, mode index, renderer and a NEW unique run name; recorded `work/coverage098-*-plan.json` and replay files specify the exact controller steps and vblank stops. The normal boot replay, original disc contents, config, DLL directory and existing source074 pack are retained locally. Run names are immutable. Example: `work/capture-coverage098.py space-kessel --mode-index 1 --renderer gpu --name coverage099-space-kessel-gcw-1flag-gpu`.', '',
    'Grouped gameplay captures: `outputs/RENDERING-098.md`. Full evidence: `outputs/COVERAGE-098.json`, `TEXTURES-098-state.json`, `TEXTURE-MUTABILITY-098.json` and catalog 098. Source-only snapshot and independent receipt: `SOURCE-098.zip`, `SOURCE-098-manifest.json`, `SOURCE-098-receipt.json`. Snapshot excludes proprietary game/test assets, dependencies and binaries; keep those retained directories separately. The receipt records the final checkpoint and capture-document hashes without a circular self-hash.', '',
    '## SHA-256', '',
    f"- Native executable: `{coverage['native_binary_sha256']}`",
    f"- BOOT.BIN: `{coverage['boot_sha256']}`",
]
hash_names = ['work/texture-catalog098/catalog.json','work/texture-catalog098/index.html',
              'outputs/COVERAGE-098.json','outputs/TEXTURE-MUTABILITY-098.json',
              'outputs/TEXTURES-098-state.json','outputs/RENDERING-098.md',
              'outputs/TEXTURE-SOURCES-095.json','outputs/FOG-097-final-build-tests.txt']
lines += [f'- {name}: `{sha(name)}`' for name in hash_names]
lines += ['', '## Remaining work', '',
    'Complete the unvisited map/era/mode routes, longer movement/combat and space-flight checks; campaign/first-mission progression and modern-control gameplay acceptance remain unfinished. Investigate dark surfaces and other rendering differences with concrete comparisons before changing shading. Continue dumping originals and let the user supply exact manual replacements. Verify model/texture override coverage in actual gameplay. The 151 runtime-only origins remain unresolved; this audit does not eliminate incomplete dynamic coverage or unknown per-draw framebuffer writes.', '',
    'No new mipmap/filtering work, channel swaps, rotation, image synthesis, upscales, dependency downloads, commit or push occurred in 098.', '']
(root/'outputs/CHECKPOINT-098.md').write_text('\n'.join(lines), encoding='utf-8')
print(json.dumps({'checkpoint_sha256':sha('outputs/CHECKPOINT-098.md'),
                  'captures_sha256':sha('outputs/RENDERING-098.md'),
                  'grouped_captures':len(shots), 'goal':'active/incomplete'}, indent=2))
