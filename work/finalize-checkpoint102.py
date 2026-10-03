"""Finalize verified new map variants, manual catalog and grouped real captures."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent.parent
read=lambda p:json.loads((root/p).read_text())
sha=lambda p:hashlib.file_digest((root/p).open('rb'),'sha256').hexdigest()
c=read('outputs/COVERAGE-102.json');s=read('outputs/TEXTURES-102-state.json')
v=read('outputs/COVERAGE-102-visual.json');m=read('outputs/TEXTURE-MUTABILITY-102.json')
catalog=read('work/texture-catalog102/catalog.json');prior=read('outputs/PRIOR-102-verification.json')
assert len(c['runs'])==8 and len(v['runs'])==8
assert all(r['exit_code']==0 and not r['timed_out'] for r in c['runs'])
assert not s['changed_native_sha256']
ordinary=[a for a in catalog['coverage'] if a['archive'].startswith(('ENVS/CLASSIC/','ENVS/PREQUEL/'))]
assert len(ordinary)==34 and all(a['successful_runs_opened'] for a in ordinary)
assert v['menu']['options']==['Galactic Civil War','Clone Wars'] and v['menu']['selected']=='Galactic Civil War'
report=['# New map/era rendering checks — checkpoint 102','',
        'Seven newly visited ordinary archive variants and one era-menu probe finished cleanly. Each gameplay capture follows normal boot/menu/launch/spawn controller inputs. Actual map/era UMD opens, native/BOOT/config/replay hashes, original dump identities and lossless 1280×720 output were verified. These are spawn diagnostics, not full matches, traversal, modern movement or flight acceptance.','',
        'All images below are actual headless 16:9 1280×720 output with FXAA. Gameplay GPU uses retained 4× MSAA and software reference raster; menu software enables HD near capture. No mipmap/filtering changes, authored texture transforms, matching, new bindings or upscales. Existing source074 pack remains partial and unchanged.','']
for r in c['runs']:
    name=r['name'];p=f'outputs/{name}-fxaa.png'
    assert sha(p)==c['screenshot_sha256'][p]
    report += [f'## {name}','',v['runs'][name],'',
               f'![{name}: actual 1280×720 with FXAA]({root.as_posix()}/{p})','',
               f'[Unfiltered render]({root.as_posix()}/outputs/{name}-unfiltered.png)','']
report += ['Every ordinary Classic/Prequel ENVS archive path has now been opened in a retained successful run. This does not prove all game modes, all textures/effects or every part of each map. Campaign/Galactic Conquest runtime coverage and independent original-PSP appearance remain incomplete.','']
(root/'outputs/RENDERING-102.md').write_text('\n'.join(report),encoding='utf-8')
counts=s['counts']
lines=['# Checkpoint 102 — remaining ordinary map variants','',
       'Status: verified concrete progress; goal remains active/incomplete. Human steering remains rendering improvements and original dumps for manual matching. Mipmap/filtering item #2 remains skipped. No authored channels/orientation changes, automatic matching, new bindings or upscales.','',
       '## Current-state revalidation and exact changes','',
       f"The prior turn was progress: five bounded modern movement/fire checks, new original/runtime observations, updated manual catalog and SOURCE-101. At this turn's start, all {prior['verified_source_files']:,} source archive entries and {prior['verified_artifact_files']} receipt artifacts were rehashed against current files. Archive SHA-256 `{prior['source_archive_sha256']}`. Verification did not rely on the conversation summary alone.",'',
       f"All {s['unchanged_native_source_files']} native source files and the executable are unchanged from SOURCE-101. No native build or rendering implementation change occurred. The 11 rendering tests last passed in checkpoint 100; retained log identities/results were verified and not repeated for evidence-tool-only changes. Native SHA-256 `{c['native_binary_sha256']}`.",'',
       'New 102 catalog/browser, bounded-run verification, source snapshot/receipt and checkpoint tools preserve frozen historical artifacts. Reference substitutions target filenames/checkpoint paths, preserving numeric settings and embedded hashes. Root manual browser launcher/guide and coverage TODO are refreshed after final evidence verification. No run/save state, game positions, camera matrices or guest input values were injected beyond normal controller replay.','',
       '## Completed runtime checks','',
       'Normal controller input visited six previously unopened Prequel variants (Korriban, Mustafar, Ord Mantell, Saleucami, Sullust, Yavin IV) and Classic Geonosis. The Geonosis era menu was inspected first and showed Galactic Civil War selected, with Clone Wars also available. That observed option determined the launch route. Planned archive names alone were not accepted as selection evidence.','',
       '| Run | Actual expected UMD archive opened | Renderer | Stop vblank | Seconds |',
       '| --- | --- | --- | ---: | ---: |']
for r in c['runs']:
    lines.append(f"| {r['name']} | {r['expected_archive'] or 'Era menu; no new gameplay archive expected'} | {r['renderer']} | {r['stop_vblank']} | {r['elapsed_seconds']:.3f} |")
lines += ['','All eight runs finished exit 0 at requested diagnostic stops without timeout. GPU strict/readback enabled, hardware transform/culling disabled, software reference raster retained, zero missing textures. Real output is 1280×720 with FXAA and unfiltered versions preserved; no native screenshots were enlarged. GPU is HD throughout, menu software enables HD near capture; elapsed times are not backend benchmarks. All runs dump original decoded textures before replacement lookup.','',
          '## Visual findings','']
lines += [f'- {n}: {finding}' for n,finding in v['runs'].items()]
lines += ['','Grouped eight-image report: `RENDERING-102.md`. Visual inspection is separate from automated terminal/hash/original-pixel assertions. No physical XInput test, full gameplay success or independent PSP visual parity is claimed. Existing coarse art/character/fog concerns are not repaired by these map checks.','',
          '## Coverage and manual provenance','',
          f"All {len(ordinary)}/{len(ordinary)} ordinary Classic/Prequel ENVS archive paths have now been opened in retained successful runs. Total ENVS opens are {counts['env_archives_opened']}/47. The remaining unvisited paths are Campaign and Galactic Conquest resources. This is archive-open coverage, not distinct-map, all-mode, full-traversal or all-dynamic-texture acceptance.",'',
          f"New runs encountered {c['texture_ids_in_new_runs']:,} distinct originals, {len(c['newly_catalogued_ids'])} absent from frozen catalog 101 and {len(c['newly_runtime_observed_ids'])} newly runtime-observed. Consolidated originals: {s['merged_original_ids']:,} IDs in {s['merged_image_files']:,} verified PNG/TGA files. Runtime observations: {counts['runtime_manifests']} manifests, {counts['runtime_unique_ids']:,} IDs.",'',
          f"Static inventory remains {counts['archive_containers']} Asura containers, {counts['texture_archives']} texture archives, {counts['archive_texture_chunks']:,} texture chunks, {counts['archived_mip_occurrences']:,} mip occurrences and {counts['archived_unique_ids']:,} exact archived RGBA identities. No unsupported static headers, uncatalogued texture archives, runtime identity errors or pack errors reported.",'',
          '| Provenance | Original IDs |','| --- | ---: |']
lines += [f'| {k} | {n} |' for k,n in counts['status_counts'].items()]
lines += ['',f"Mutable-source audit: {m['case_count']} same-run source configurations, {m['member_ids']} member IDs, {m['render_target_ids_in_cases']} render-target member IDs and {m['unresolved_origin_ids_in_cases']} origin-unresolved IDs. Cases are not assets. Render-target classification requires same-run observed VRAM evidence; cross-run addresses do not imply continuity. Every original and content filename is retained; changing frame captures remain hidden by default in the manual browser.",'',
          f"All {c['pack074_files_unchanged']} existing source074 image files rehashed unchanged. The user's authoring orientation/channels are preserved. No matching based solely on similar names or inferred camera appearance occurred. Source indexes are copied byte-for-byte from frozen 101 with recorded hashes; prior 095 intake is 13,820 images in 12 conversion archives and was not completely re-audited again. Runtime IDs with different alpha retain their own identities even when dimensions/RGB match an archived named asset.",'',
          '## Reproducible state','',
          'Native build remains Windows x64 Release using retained CMake/Ninja, MSVC 14.44.35207, SDK 10.0.26100.0 and `work/windows-sdk`. Build: `work/build-windows.cmd`; rendering tests: `work/test-rendering.cmd`. No missing dependency was proven, and no dependency request/download was made. No commit/push occurred.','',
          'Use the bundled Python with Pillow and `work/capture-coverage099.py PLANET --era ERA --renderer gpu|software --name NEW-NAME`. For menu probes add `--menu-stage era|mode|planet`. Exact inputs/stops are preserved in `work/coverage102-*-plan.json`, replay files and each immutable `work/runs/coverage102-*` folder. `verify-coverage102.py` checks all eight terminal states, actual opens, isolated/current native/BOOT/config/replay/log/capture hashes, original content identities and unchanged authored pack.','',
          '`catalog-textures102.py`, `audit-runtime-textures102.py`, `build-texture-browser102.py`, `test-texture-browser102.cjs` and `verify-texture-catalog102.py` regenerate/validate manual provenance, require all new manifests/terminal states/original IDs to be present, check original filenames/RGBA hashes, native source inventory and preserved test log hashes. Browser code-level DOM tests passed; no browser visual acceptance is claimed. Local-file browser policy remains unchanged.','',
          'SOURCE-102 ZIP/manifest and independent receipt preserve exact source/tooling state and separately record final docs, binary, compiler/build/dependency hashes. Original disc, images/models, dependencies and native run payloads remain excluded from the source-only archive and retained locally. This is not a fresh-machine build test.','',
          f"- Native SHA-256: `{c['native_binary_sha256']}`",f"- BOOT SHA-256: `{c['boot_sha256']}`"]
for p in ['outputs/PRIOR-102-verification.json','outputs/COVERAGE-102.json',
          'outputs/COVERAGE-102-visual.json','outputs/TEXTURES-102-state.json',
          'outputs/TEXTURE-MUTABILITY-102.json','work/texture-catalog102/catalog.json',
          'work/texture-catalog102/index.html','outputs/TEXTURE-102-browser-tests.txt','outputs/RENDERING-102.md']:
    lines.append(f'- {p}: `{sha(p)}`')
lines += ['','## Remaining work','',
          'Campaign/Galactic Conquest runtime routes, full first-mission modern controls, longer traversal/combat/flight, all mode/effect/UI/dynamic texture census, manual authored replacement coverage, independent PSP appearance, Space Kashyyyk player fade, CPU framebuffer writes/feedback coherence, guest 16-bit stencil and wider model/material/primitive parity remain incomplete. Mipmap/filtering work stays skipped.','']
(root/'outputs/CHECKPOINT-102.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'checkpoint_sha256':sha('outputs/CHECKPOINT-102.md'),'render_report_sha256':sha('outputs/RENDERING-102.md'),'goal':'active/incomplete'},indent=2))
