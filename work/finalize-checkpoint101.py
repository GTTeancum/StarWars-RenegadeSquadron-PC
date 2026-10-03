"""Write grouped 720p evidence and exact checkpoint only after verification."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent.parent
read=lambda p:json.loads((root/p).read_text())
sha=lambda p:hashlib.file_digest((root/p).open('rb'),'sha256').hexdigest()
c=read('outputs/COVERAGE-101.json')
s=read('outputs/TEXTURES-101-state.json')
v=read('outputs/COVERAGE-101-visual.json')
m=read('outputs/TEXTURE-MUTABILITY-101.json')
assert len(c['runs'])==5 and len(v['gameplay'])==5
assert all(r['exit_code']==0 and not r['timed_out'] for r in c['runs'])
assert not s['changed_native_sha256']
assert not v['pending']
for name,digest in v['supplemental_native_sha256'].items():assert sha(name)==digest,name
report=['# Movement and rendering checks — checkpoint 101','',
        'Five bounded controller-only routes finished cleanly. Each route enabled the existing modern gamepad sampler, moved forward, turned with the right stick, moved/fired with the right trigger, strafed/fired, and released inputs. Actual infantry input getter traces confirm movement, independent turning, trigger press and release. The second space route adds backward retreat and a left turn to leave camera-obstructing geometry. These are short routes, not full matches or enemy-kill/ship-flight acceptance.','',
        'Final views below are actual headless 16:9 1280×720 output with FXAA, losslessly encoded. GPU uses retained 4× MSAA. Software enables HD near its final capture; timings are not backend benchmarks. No mipmap/filtering changes, authored texture transforms, new bindings or upscales. The existing source074 pack remains partial and unchanged.','']
for r in c['runs']:
    name=r['name'];p=f'outputs/{name}-fxaa.png'
    assert sha(p)==c['screenshot_sha256'][p]
    report += [f'## {name}','',v['gameplay'][name],'',
               f'![{name}: actual 1280×720 with FXAA]({root.as_posix()}/{p})','',
               f'[Unfiltered render]({root.as_posix()}/outputs/{name}-unfiltered.png)','']
    if '-clear-' in name:
        report += [f'[Same-frame native software reference, 480×272]({root.as_posix()}/outputs/{name}-native-final.png)','']
report += ['No independent original-PSP visual reference or whole-frame equality is claimed. Physical XInput hardware was not exercised by these headless diagnostic samples. Existing fog, art and GPU limitations remain documented in the checkpoint.','']
(root/'outputs/RENDERING-101.md').write_text('\n'.join(report),encoding='utf-8')
counts=s['counts']
lines=['# Checkpoint 101 — modern movement, firing and original dumps','',
       'Status: verified bounded progress; goal remains active/incomplete. Latest user scope is rendering improvements and original dumping for manual matching. Item #2 (mipmap/filtering work) stays skipped. Authored channels/orientation are untouched; no automatic matching, new binding or upscale occurred.','',
       '## Exact changes and preserved state','',
       '`capture-motion101.py` extends the retained normal boot/menu route with existing controller-only pause/commands and gamepad diagnostic sampling. Six intervals add 450 vblanks: neutral enable 30, forward 180, independent right-stick turn 45, forward/right-trigger 90, strafe/right-trigger 60 and release/settle 45. Optional `--retreat` adds backward 120, left turn 30 and settle 45, totaling 645 additional vblanks. Commands and raw samples are journaled before publication; final command extends one vblank past the diagnostic stop to avoid pausing before termination. Immutable run names prevent overwrite. No guest positions, camera matrices, save states or memory values are injected.','',
       'New 101 evidence tools verify actual input getter transitions, native/BOOT/config/replay identities, accepted command intervals, final captures, original content hashes, catalog provenance and unchanged authored pack files. Catalog/browser and root manual instructions are updated; frozen 100 artifacts are retained. During preparation, broad checkpoint-number substitution also changed CSS percentages, VM timeout literals and the embedded expected native hash. CSS/timeouts were corrected before browser generation. The first runtime verifier rejected the altered expected hash; the failure is retained in MOTION-101-verification.txt, and surgical reference substitutions restored the exact unchanged native identity. Initial four-route success evidence is retained separately; final five-route verification is authoritative. Guessed source filenames and two patch applications failed during preparation without partial edits or build/test execution. Existing ignored Python bytecode caches are excluded from the native source inventory check.','',
       f"Every {s['unchanged_native_source_files']:,} prior native source file was rehashed against SOURCE-100 and remains unchanged. No native implementation/build change occurred. Executable SHA-256 stays `{c['native_binary_sha256']}`. Checkpoint 100's 11 rendering tests passed; their original logs/hashes were checked, not rerun for tool-only changes. No new rendering fix is claimed in 101.",'',
       '## Completed routes and observed input','',
       '| Run | Actual archive opened | Stop vblank | Seconds |',
       '| --- | --- | ---: | ---: |']
for r in c['runs']:
    lines.append(f"| {r['name']} | {r['expected_archive']} | {r['stop_vblank']} | {r['elapsed_seconds']:.3f} |")
lines += ['','All five runs reached their requested diagnostic stop, exit 0, no timeout. Requested map/era selections were confirmed by actual UMD archive opens. GPU retained the software reference raster, disabled hardware transform/culling, enabled strict/readback checks and reported zero missing textures. Captures are actual 720p renders, never resized native frames. Original texture dumping remained enabled throughout each route.','',
          '| Run | Forward | Right-stick turn | Fire | Strafe | Release fire |',
          '| --- | --- | --- | --- | --- | --- |']
for r in c['runs']:
    a=r['verified_action_transitions']
    cells=[]
    for label in ['forward','look-right','forward-fire','strafe-fire','release-settle']:
        x=a[label][0];cells.append(f"id {x['id']} = {x['value']:.6g} at {x['frame']}")
    lines.append('| '+r['name']+' | '+' | '.join(cells)+' |')
lines += ['','Raw gamepad samples use the same normalizer/context/action path as production input. Headless samples do not test a physical XInput device. Input getter evidence proves that the game consumed these requested controls; it does not prove a kill, completed objective or unrestricted traversal. The space route remains on foot in the hangar; no flight claim. AI behavior differs across runs, and CPU/GPU captures are not whole-frame parity assertions.','',
          '## Visual inspection','']
lines += [f'- {name}: {finding}' for name,finding in v['gameplay'].items()]
lines += ['','Grouped final images and unfiltered links: `RENDERING-101.md`. Native pause images and logs are retained as intermediate controller-route evidence; they were not enlarged into the 720p baseline. The initial space route is preserved as camera-obstruction evidence and prompted a fresh retreat route.','',
          '## Original textures and manual catalog','',
          f"New routes encountered {c['texture_ids_in_new_runs']:,} distinct originals: {len(c['newly_catalogued_ids'])} absent from frozen catalog 100 and {len(c['newly_runtime_observed_ids'])} newly runtime-observed. Consolidated catalog now has {s['merged_original_ids']:,} IDs in {s['merged_image_files']:,} verified original PNG/TGA files. {counts['runtime_manifests']} retained runtime manifests contain {counts['runtime_unique_ids']:,} runtime IDs. {counts['env_archives_opened']}/47 ENVS archive paths have been opened in successful retained runs; these are archive paths, not distinct maps or full traversal counts.",'',
          f"Static inventory remains {counts['archive_containers']} Asura containers, {counts['texture_archives']} texture archives, {counts['archive_texture_chunks']:,} texture chunks, {counts['archived_mip_occurrences']:,} archived mip occurrences and {counts['archived_unique_ids']:,} exact archive identities. No unsupported headers, uncatalogued texture archives, runtime identity errors or pack errors reported.",'',
          '| Provenance | Original IDs |','| --- | ---: |']
lines += [f'| {k} | {n} |' for k,n in counts['status_counts'].items()]
lines += ['',f"Mutable-source audit: {m['case_count']} same-run source-configuration cases, {m['member_ids']} member IDs, {m['render_target_ids_in_cases']} render-target member IDs and {m['unresolved_origin_ids_in_cases']} origin-unresolved member IDs. Cases are not distinct assets. Render-target classification requires actual same-run VRAM target evidence; cross-run addresses do not establish continuity. All original samples and filenames remain available, including changing frame captures hidden by default.",'',
          f"All {c['pack074_files_unchanged']} source074 authored image files rehashed unchanged. No image rotation/channel swap/resizing was applied. Exact source indexes are copied byte-for-byte from frozen 100 with recorded hashes; 095's 13,820 images in 12 conversion archives were not fully re-audited again. User replacement precedence remains DDS > TGA > PNG, with valid explicit mesh material replacements winning. Dump identity precedes override lookup.",'',
          '## Reproduction and verified hashes','',
          'Build remains Windows x64 Release: `work/build-windows.cmd`; rendering checks: `work/test-rendering.cmd`. Retained CMake/Ninja, MSVC 14.44.35207, SDK 10.0.26100.0 and local DLL dependencies are unchanged. No dependency request/download was needed.','',
          'Use the bundled Python with Pillow and `work/capture-motion101.py PLANET --era ERA --renderer gpu|software --name NEW-NAME`, optionally `--retreat`. Accepted names/settings, exact boot/menu replays, motion plans, raw gamepad records, command acknowledgements, native logs and terminal states are retained under `work/runs` and matching `work/*-plan.json`. Runs last 450 or 645 additional vblanks after spawn with a 900-second outer bound; controller waits retain the runner bound.','',
          '`verify-coverage101.py` validates all five runtime outcomes and input transitions. `catalog-textures101.py`, `audit-runtime-textures101.py`, `build-texture-browser101.py`, `test-texture-browser101.cjs` and `verify-texture-catalog101.py` regenerate and validate manual provenance. The final catalog is refreshed after the retreat run and required to contain every new terminal run, unchanged manifest hash and original ID. Browser code-level DOM checks passed; no browser visual acceptance is claimed. Local-file browser policy remains unmodified. Source-only SOURCE-101 snapshot/manifest and independent receipt record exact source/tooling state, compiler/dependency identities and final document hashes. Proprietary assets/dependencies/binaries remain excluded and separately retained locally. Snapshot is not a fresh-machine build test. No commit/push occurred.','',
          f"- Native SHA-256: `{c['native_binary_sha256']}`",f"- BOOT SHA-256: `{c['boot_sha256']}`"]
for p in ['outputs/COVERAGE-101.json','outputs/COVERAGE-101-visual.json',
          'outputs/MOTION-101-verification.txt','outputs/MOTION-101-all-routes-verification.txt',
          'outputs/TEXTURES-101-state.json','outputs/TEXTURE-MUTABILITY-101.json',
          'work/texture-catalog101/catalog.json','work/texture-catalog101/index.html',
          'outputs/TEXTURE-101-browser-tests.txt','outputs/RENDERING-101.md']:
    lines.append(f'- {p}: `{sha(p)}`')
lines += ['','## Remaining work','',
          'Independent original-PSP appearance references, unvisited map/era/mode routes, longer combat and flight, first-mission modern-controls completion, explicit model/material visual acceptance, manual texture replacement coverage and dynamic/UI census remain open. GPU 5551/4444 stencil, CPU framebuffer writes/feedback coherence and wider primitive/model parity are still incomplete. Coarse art is not repaired by these checks; mipmap/filtering work remains skipped.','']
(root/'outputs/CHECKPOINT-101.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'checkpoint_sha256':sha('outputs/CHECKPOINT-101.md'),'render_report_sha256':sha('outputs/RENDERING-101.md'),'goal':'active/incomplete'},indent=2))
