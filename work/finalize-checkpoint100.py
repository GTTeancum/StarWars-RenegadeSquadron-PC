"""Finalize software-fog repair and grouped verified before/after captures."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent.parent
read=lambda p:json.loads((root/p).read_text())
sha=lambda p:hashlib.file_digest((root/p).open('rb'),'sha256').hexdigest()
coverage=read('outputs/COVERAGE-100.json')
state=read('outputs/TEXTURES-100-state.json')
mutable=read('outputs/TEXTURE-MUTABILITY-100.json')
comparisons=read('outputs/FOG-100-comparisons.json')
visual=read('outputs/COVERAGE-100-visual.json')
assert len(coverage['runs'])==4
assert all(r['exit_code']==0 and not r['timed_out'] for r in coverage['runs'])
assert state['native_binary_sha256']==coverage['native_binary_sha256']
assert '100% tests passed out of 11' in (root/'outputs/FOG-100-final-build-tests.txt').read_text()
report=['# Software fog comparisons — checkpoint 100','',
        'The software renderer now applies fragment fog to shaded RGB after texture sampling. Alpha rejection/blending, screen-space HUD and clear behavior are protected by actual GE raster tests. All 11 rendering tests pass; native/720p boundary, clipping, unequal perspective and GPU agreement are checked.','',
        'These are actual 1280×720 headless captures with FXAA, losslessly encoded. GPU uses 4× MSAA; software activates HD near capture, so elapsed times are not a performance comparison. The source074 pack remains partial and unchanged. No mipmap/filtering changes, image resizing, authored texture transforms or new bindings.','',
        'Before/after runs share controller inputs, stop, BOOT, output settings and unchanged software config/pack. AI positions/reinforcements vary, so this is not deterministic whole-frame equality or independent original-PSP visual acceptance. The older software build did not shade fragment fog.','']
for row in comparisons['comparisons']:
    title='Hoth — Galactic Civil War' if row['scenario']=='hoth-gcw' else 'Mygeeto — Clone Wars'
    report += [f'## {title}','',visual['gameplay']['coverage100-'+row['scenario']+'-software'],'']
    for label,key in [('Before — software without fragment fog','before_capture'),
                      ('After — repaired software fog','after_capture'),
                      ('Current GPU reference','gpu_capture')]:
        path=row[key]
        assert sha(path)==row['screenshot_sha256'][path]
        report += [f'### {label}','',f'![{title}: {label}]({root.as_posix()}/{path})','']
        if key!='before_capture':
            raw=path.replace('-fxaa.png','-unfiltered.png')
            assert raw in coverage['screenshot_sha256'] and sha(raw)==coverage['screenshot_sha256'][raw]
            report += [f'[Unfiltered render]({root.as_posix()}/{raw})','']
report += ['Mygeeto’s dark distant interior is now present in both renderers. Agreement does not prove correct guest fog state or original PSP appearance; no arbitrary brightening is applied. Coarse existing artwork and wider rendering/gameplay acceptance remain unresolved.','']
(root/'outputs/RENDERING-100.md').write_text('\n'.join(report),encoding='utf-8')
c=state['counts']
lines=['# Checkpoint 100 — software fragment fog repair','',
       'Status: concrete progress; goal remains active/incomplete. Previous turn finalized 099 texture/map evidence and a verified 1,528-file source-only snapshot. Latest user scope remains rendering improvements and original dumps for manual matching. Item #2 (mipmap/filtering changes) remains skipped. Authored channels/orientation are unchanged; no new matching, binding or upscale was generated.','',
       '## Verified implementation','',
       '- Software FragmentSetup now decodes fog enable/color and disables fog for through-mode or clear draws. Its cache keys include vertex mode, fog enable and fog color; the reserved final address-hash slot remains last.',
       '- Triangle fog uses perspective interpolation of raw coefficients through clipping, then clamps at the fragment. Point/line paths supply decoded/interpolated coefficients. Supported screen-space rectangles bypass fog; projected GE rectangles remain unsupported as before.',
       '- RGB fog is blended after texture/material shading and before alpha testing/blending. Source alpha is untouched. HD shadow rendering uses the same behavior; guest texture bytes and authored images are not altered.',
       '- Added `override_fog.cpp`, its CMake target and inclusion in the standard rendering test script. Extended the actual DX12 test with an unequal-clip-W fixture to check GPU/software agreement. No GPU backend implementation edit occurred in 100.','',
       'The interpolation/clamping and RGB-only post-texture behavior follow the existing GPU path. Primary reference: [PPSSPP fragment shader generation](https://github.com/hrydgard/ppsspp/blob/master/GPU/Common/FragmentShaderGenerator.cpp). This is independent implementation and synthetic parity evidence, not an original-PSP game appearance certification.','',
       '## Failures preserved and final tests','',
       'The new regression first failed on the old renderer with native samples 255/255/255/255, proving that fog was omitted. The first repair yielded correct 0/52/154/255 samples but failed color mutation because new cache keys displaced the reserved final slot. Moving the placeholder to the end repaired cache invalidation. Both failed logs are retained; no success claim relies on them. Two initial direct test launch attempts used incorrect relative/output paths before CTest correctly invoked the target; no tests ran in those failed launches.','',
       'Final native build and all 11 rendering tests PASS: texture, MSH, rendering, new fog, DX12, skin, commands, pose, model, stencil and display. Actual sampled results:','',
       '| Fixture | Verified samples |','| --- | --- |',
       '| Native fog boundary | 0 / 52 / 154 / 255 |',
       '| Native clipped triangle | 0 / 69 / 171 / 255 |',
       '| Real 1280×720 software boundary | 0 / 51 / 153 / 255 |',
       '| Unequal clip W — native / HD software / actual GPU | 85 / 85 / 85 |','',
       'Additional actual raster assertions cover fog color/enable mutation, textured REPLACE order, source-alpha equality/rejection, source-alpha blending with retained destination stencil/alpha, projected points/lines, through-mode HUD point/sprite and color/alpha clear. Tests exercise real GE inputs and raster outputs rather than duplicating the fog arithmetic. Existing GPU boundary/packed, texture mutation, alpha, depth, stencil and HD checks remain passing.','',
       '## Gameplay and before/after comparison','',
       'Four new runs finished exit 0 without timeout. Hoth GCW and Mygeeto Clone Wars actual archive opens are verified for both renderers. Controller replay/stop/BOOT/output settings are identical within each pair and to retained 096 software baselines; software config and source074 image files are unchanged. Actor poses/reinforcements differ across executions, so full-image equality is not expected.','',
       '| Run | Renderer | Stop vblank | Seconds | Actual archive opened |',
       '| --- | --- | ---: | ---: | --- |']
for r in coverage['runs']:
    lines.append(f"| {r['name']} | {r['renderer']} | {r['stop_vblank']} | {r['elapsed_seconds']:.3f} | {r['expected_archive']} |")
lines += ['','All gameplay captures are actual 16:9 1280×720 headless output with FXAA; GPU uses 4× MSAA throughout, CPU reference raster retained, hardware transform/culling off. Software enables HD near capture; timings are not a backend benchmark. GPU reported zero missing textures and drew existing replacements. All 355 source074 images rehashed unchanged; that partial pack is not full desired upgrade coverage.','']
lines += [f'- {name}: {finding}' for name,finding in visual['gameplay'].items()]
lines += ['','Hoth’s older software view had a sharp distant ridge; repaired software fog fades it toward the GPU reference. Mygeeto’s older software view had a brighter detailed distant interior; repaired software and GPU both fade it dark. This resolves the omitted-software-fog comparison flaw, not the question of correct original-PSP appearance or all dark surfaces. Grouped six-image before/after/reference report is `RENDERING-100.md`.','',
       '## Original dumps and provenance','',
       f"New runs encountered {coverage['texture_ids_in_new_runs']} distinct originals, {len(coverage['newly_catalogued_ids'])} absent from frozen catalog 099 and {len(coverage['newly_runtime_observed_ids'])} newly runtime-observed. Consolidated originals remain {state['merged_original_ids']:,} IDs in {state['merged_image_files']:,} verified PNG/TGA files. Runtime observations now span {c['runtime_manifests']} manifests and {c['runtime_unique_ids']:,} IDs.",'',
       f"Static inventory remains {c['archive_containers']} Asura containers, {c['texture_archives']} texture archives, {c['archive_texture_chunks']:,} texture chunks, {c['archived_mip_occurrences']:,} mip occurrences and {c['archived_unique_ids']:,} named exact RGBA identities. Retained successful runs opened {c['env_archives_opened']}/47 ENVS archive paths, not distinct-map counts/full traversal. Shared content observed elsewhere does not prove a map was visited.",'',
       '| Provenance | IDs |','| --- | ---: |']
lines += [f'| {k} | {v} |' for k,v in c['status_counts'].items()]
lines += ['','Same-run render-target classification remains narrow: actual VRAM region, observed canonical target, unswizzled format 3, 512×512 and stride 512; original pixels and every content filename are retained. Changing frame captures are hidden by default in the manual browser. Neither asset names nor complete per-draw write histories are inferred.', '',
       f"Mutable-source audit: {mutable['case_count']} configuration cases, {mutable['member_ids']} member IDs, including {mutable['render_target_ids_in_cases']} render-target IDs and {mutable['unresolved_origin_ids_in_cases']} origin-unresolved IDs. Cases are not distinct assets; cross-run addresses do not imply continuity.",'',
       'No unsupported static texture headers, uncatalogued texture archives, runtime identity errors or pack errors reported. Full dynamic/UI gameplay census remains incomplete. Original source indexes were copied byte-for-byte from frozen 099 and checked against its recorded hashes; the 095 source intake remains 13,820 images from 12 archives. All original source payloads were not re-audited again this turn.','',
       '## Reproducible state and verification','',
       f"Compared with SOURCE-099, {state['unchanged_native_source_files']} prior native source files were rehashed unchanged. Changed existing native files are ge_renderer.cpp, renegade/CMakeLists.txt and tests/dx12_override.cpp; new test is tests/override_fog.cpp. The rendering script also now builds the new test. Exact changed source identities are in TEXTURES-100-state.json.",'',
       'Windows x64 Release build uses retained CMake/Ninja, MSVC 14.44.35207, SDK 10.0.26100.0 and `work/windows-sdk`. Build via `work/build-windows.cmd`; required rendering checks via `work/test-rendering.cmd`. No dependency request/download was needed. Fresh final build/test output and detailed actual sample output are saved in FOG-100-final-build-tests.txt and FOG-100-test-detail.txt.','',
       'Runtime: use the bundled Python with Pillow and `work/capture-coverage099.py` with a NEW unique run name, planet, era and renderer. Recorded `work/coverage100-*-plan.json` and replay files preserve exact controls, stop and capture vblanks. Example: `work/capture-coverage099.py mygeeto --era clone --renderer software --name coverage101-mygeeto-clone-software`. Normal boot replay, original disc, DLL directory, config and source074 pack are retained separately. Run names are immutable.','',
       '`verify-coverage100.py` verified terminal state, opens, isolated/native/BOOT/config/replay/log hashes, original RGBA identities and lossless 720p screenshots. `compare-fog100.py` verified historical capture/config hashes and replay/stop comparability. Catalog/mutable-source audits verified originals/manifests; browser code-level tests passed filter/pagination/provenance/filenames. No browser visual acceptance is claimed. `verify-texture-catalog100.py` checked every consolidated original, evidence/test hashes, expected native changes and unchanged source state.','',
       'Source-only SOURCE-100.zip, manifest and independent receipt preserve exact source/tooling state and separately record compiler/build/dependency identities. Proprietary assets, reference clones, dependencies and binaries remain excluded and retained locally. Snapshot is not a fresh-machine build test. The receipt records final documents/binary hashes without a circular self-hash. No commit/push occurred.','',
       '## SHA-256','',f"- Native: `{coverage['native_binary_sha256']}`",f"- BOOT: `{coverage['boot_sha256']}`"]
for name in ['outputs/FOG-100-before-test.txt','outputs/FOG-100-build-tests.txt',
             'outputs/FOG-100-final-build-tests.txt','outputs/FOG-100-test-detail.txt',
             'outputs/COVERAGE-100.json','outputs/FOG-100-comparisons.json',
             'work/texture-catalog100/catalog.json','work/texture-catalog100/index.html',
             'outputs/TEXTURES-100-state.json','outputs/RENDERING-100.md']:
    lines.append(f'- {name}: `{sha(name)}`')
lines += ['','## Remaining work','',
       'Obtain independent original-PSP appearance references, especially Hoth distant terrain/Mygeeto dark interior. Continue unvisited map/era/mode routes and longer movement/combat/space-flight diagnostics. Verify full first-mission modern controls and actual model/material packs. Continue manual replacement matching and original dumping. Unknown origins, incomplete dynamic census, CPU framebuffer write/feedback coherence, guest 16-bit stencil behavior and wider GPU parity remain open. Coarse artwork is not solved by fog; mipmap/filtering work remains skipped.','']
(root/'outputs/CHECKPOINT-100.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'checkpoint_sha256':sha('outputs/CHECKPOINT-100.md'),'capture_report_sha256':sha('outputs/RENDERING-100.md'),'goal':'active/incomplete'},indent=2))
