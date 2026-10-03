"""Finalize checkpoint 099 from terminal, pixel and manually inspected evidence."""
import hashlib, json
from pathlib import Path
root=Path(__file__).resolve().parent.parent
read=lambda p:json.loads((root/p).read_text())
sha=lambda p:hashlib.file_digest((root/p).open('rb'),'sha256').hexdigest()
coverage=read('outputs/COVERAGE-099.json')
state=read('outputs/TEXTURES-099-state.json')
mutable=read('outputs/TEXTURE-MUTABILITY-099.json')
visual=read('outputs/COVERAGE-099-visual.json')
assert len(coverage['runs']) == 7
assert all(r['exit_code']==0 and not r['timed_out'] for r in coverage['runs'])
assert state['native_binary_sha256']==coverage['native_binary_sha256']
assert len(visual['gameplay'])==5
for p,d in coverage['screenshot_sha256'].items():assert sha(p)==d,p
shots=[('Kashyyyk — Galactic Civil War, Conquest','kashyyyk-gcw-conquest-gpu'),
       ('Mygeeto — Galactic Civil War, Conquest','mygeeto-gcw-conquest-gpu'),
       ('Tatooine — Galactic Civil War, Conquest','tatooine-gcw-conquest-gpu'),
       ('Space Kashyyyk — Galactic Civil War, Assault','space-kashyyyk-gcw-assault-gpu'),
       ('Space Yavin — Galactic Civil War, Assault','space-yavin-gcw-assault-gpu')]
report=['# Rendering captures — checkpoint 099','',
        'Five actual 1280×720 GPU renders with 4× MSAA and FXAA. All use the final checkpoint 097 executable, headlessly captured and encoded losslessly. No image resampling, mipmap/filtering change or new texture binding. Source074 remains a partial unchanged pack.','',
        'Bounded normal-controller spawn checks, not full matches, movement/combat or ship-flight acceptance. GPU gameplay hardware transform/culling remain off and CPU reference raster is retained. Exact hashes and counters are in COVERAGE-099.json.','']
for title,suffix in shots:
    name='coverage099-'+suffix
    p='outputs/'+name
    assert p+'-fxaa.png' in coverage['screenshot_sha256']
    report += [f'## {title}','',visual['gameplay'][name]['finding'],'',
               f'![{title}]({root.as_posix()}/{p}-fxaa.png)','',
               f'[Unfiltered render]({root.as_posix()}/{p}-unfiltered.png)','']
(root/'outputs/RENDERING-099.md').write_text('\n'.join(report),encoding='utf-8')
counts=state['counts']
lines=['# Checkpoint 099 — additional map and era texture diagnostics','',
       'Status: progress; goal remains active/incomplete. Previous turn saved checkpoint 098 and its verified source snapshot. Latest user pivot is rendering improvements and original texture dumping for manual matching; item #2 (mipmap/filtering changes) remains skipped. No automatic source matches, new bindings, rotation/channel changes or upscales were generated.','',
       '## Verified changes','',
       '- Added checkpoint 099 normal-controller capture tooling and immutable run plans/replays, without guest state injection or asset substitution.',
       '- Visually verified Space Yavin at planet index 21 and its sole Galactic Civil War era. Requested first mode; actual score HUD and archive evidence are recorded with the visual observations.',
       '- Exercised five previously unopened GCW ENVS archives: Kashyyyk, Mygeeto, Tatooine, Space Kashyyyk and Space Yavin.',
       '- Consolidated newly encountered original images into a new catalog, retaining same-run render-target classification and all prior originals. Original source-index files were copied byte-for-byte from frozen 098 and checked against its hashes.',
       '- Updated the root texture browser and matching guide to the new catalog. Frozen prior catalogs/checkpoints remain unchanged.','',
       '## Runs and visual findings','',
       'All seven diagnostics terminated exit 0 without timeout: two menu probes and five GPU gameplay routes. Expected ENVS archives actually opened; this establishes entry/spawn evidence, not full gameplay acceptance. All gameplay captures are actual 16:9 1280×720 GPU output with 4× MSAA and FXAA, encoded losslessly.','',
       '| Run | Renderer | Stop vblank | Seconds | Expected archive actually opened |',
       '| --- | --- | ---: | ---: | --- |']
for r in coverage['runs']:
    lines.append(f"| {r['name']} | {r['renderer']} | {r['stop_vblank']} | {r['elapsed_seconds']:.3f} | {r['expected_archive'] or 'Menu probe'} |")
lines += ['','Each GPU run reported zero missing textures, rendered frames/draws and uploaded/drew existing pack replacements. GPU diagnostic counters establish use of some replacements, not complete desired upgrade coverage. All 355 source074 image files were rehashed unchanged.','']
for title,suffix in shots:
    lines.append(f"- {title}: {visual['gameplay']['coverage099-'+suffix]['finding']}")
lines += ['','## Original coverage and unresolved cases','',
       f"New runs encountered {coverage['texture_ids_in_new_runs']:,} distinct original RGBA identities; {len(coverage['newly_catalogued_ids']):,} were absent from frozen 098 and {len(coverage['newly_runtime_observed_ids']):,} were newly runtime-observed. These are content IDs, not named-material counts.",'',
       f"Consolidated originals: {state['merged_original_ids']:,} IDs in {state['merged_image_files']:,} verified PNG/TGA files. Static inventory: {counts['archive_containers']} Asura containers, {counts['texture_archives']} texture archives, {counts['archive_texture_chunks']:,} chunks, {counts['archived_mip_occurrences']:,} mip occurrences and {counts['archived_unique_ids']:,} exact archived RGBA IDs. Runtime: {counts['runtime_unique_ids']:,} IDs across {counts['runtime_manifests']} retained manifests.",'',
       f"Successful retained runs opened {counts['env_archives_opened']} of 47 ENVS archive paths. This is not a distinct-map count, full traversal or complete dynamic/UI gameplay coverage. Shared content seen in any run does not prove another map was visited.",'',
       '| Provenance category | IDs |','| --- | ---: |']
lines += [f'| {k} | {v} |' for k,v in counts['status_counts'].items()]
lines += ['','Render-target classification remains narrow: actual VRAM region, a same-run observed canonical target, unswizzled format 3, 512×512 and stride 512. Recorded render-target evidence logs/reports were rehashed. It does not reconstruct each draw’s write history or assign asset names. All originals remain available; changing frame captures are hidden by default with an explicit inclusion checkbox.', '',
       f"Mutable-source audit: {mutable['case_count']} source-configuration cases, {mutable['member_ids']} member IDs, {mutable['render_target_ids_in_cases']} render-target member IDs and {mutable['unresolved_origin_ids_in_cases']} origin-unresolved member IDs. Cases are not distinct assets; cross-run equal addresses do not prove continuity.",'',
       'No unsupported static texture headers, uncatalogued texture archives, runtime pixel-identity errors or pack errors were found. Full dynamic coverage is still unproven. Original source intake 095 remains 13,820 images from 12 conversion archives; its frozen source indexes are unchanged, but all source payloads were not re-audited anew this turn. User-authored orientation/channels remain untouched.','',
       '## Verification and reproducible build state','',
       f"All {state['unchanged_native_source_files']} native source files recorded under `work/project/source/` in SOURCE-098 and the final executable were rehashed unchanged. No native rebuild/edit occurred in 099. The final 097 rendering suite’s 10 passing tests remain applicable to this unchanged build, including actual fog boundary and packed-alignment GPU regressions. Failing pre-fix evidence remains preserved.",'',
       '`verify-coverage099.py` verified terminal states, archive opens, native/isolated executable/BOOT identities, configs, input replays, per-run originals, actual raw/FXAA 720p pixels and unchanged pack files. `catalog-textures099.py` checked static/runtime identities and carried the verified original source indexes forward. `audit-runtime-textures099.py` checked manifests. `test-texture-browser099.cjs` passed code-level filtering, pagination, provenance and filenames with a DOM stand-in; browser visual acceptance is not claimed. `verify-texture-catalog099.py` verified every consolidated original, report/evidence hashes and unchanged native sources. A premature report-finalizer invocation failed because the live verifier had not yet emitted its state JSON; it was rerun after successful verification. `DOCUMENT-099-premature-finalize.txt` preserves that sequencing failure; no native state changed.','',
       'Build remains Windows x64 Release, CMake/Ninja, MSVC 14.44.35207, SDK 10.0.26100.0 and retained `work/windows-sdk`. Rebuild via `work/build-windows.cmd`; rendering suite via `work/test-rendering.cmd`. No new dependency request/download was needed. Source snapshot records current build scripts, CMakeCache, compiler/tool/dependency hashes; not a fresh-machine build test.','',
       'Reproduce using the bundled Python with Pillow and `work/capture-coverage099.py`, a NEW unique run name, requested planet, era, mode and renderer. Exact inputs/stops are in `work/coverage099-*-plan.json` and replay files; original disc, DLL directory, config and source074 pack are retained. Example: `work/capture-coverage099.py space-yavin --renderer gpu --name coverage100-space-yavin-gcw-assault-gpu`. Do not reuse immutable run names.','',
       'Artifacts: `RENDERING-099.md` groups the final gameplay captures; `COVERAGE-099.json` and `COVERAGE-099-visual.json` record terminal/hash and separately inspected visual evidence; catalog 099 plus `TEXTURES-099-state.json` and `TEXTURE-MUTABILITY-099.json` preserve originals/provenance. `SOURCE-099.zip`, manifest and independent receipt preserve source-only state, excluding proprietary assets, dependencies and binaries retained separately. The receipt records final document hashes without a circular self-hash.','',
       '## SHA-256','',f"- Native: `{coverage['native_binary_sha256']}`",f"- BOOT: `{coverage['boot_sha256']}`"]
for name in ['work/texture-catalog099/catalog.json','work/texture-catalog099/index.html',
             'outputs/COVERAGE-099.json','outputs/COVERAGE-099-visual.json',
             'outputs/TEXTURES-099-state.json','outputs/TEXTURE-MUTABILITY-099.json',
             'outputs/RENDERING-099.md','outputs/FOG-097-final-build-tests.txt']:
    lines.append(f'- {name}: `{sha(name)}`')
lines += ['','## Remaining work','',
       'Complete unopened archive/era/mode routes and longer movement/combat/space-flight diagnostics. Full first-mission modern-controls gameplay remains incomplete. Coarse existing artwork, dark surfaces and broader GPU parity remain unresolved; brighter software output is not a correctness reference because software fragment fog is still omitted. Repair that concrete omission with boundary/alpha tests before using software as a fog comparison. Continue original dumps and manual replacement matching; no full dynamic census or universal model/material gameplay acceptance is claimed.','',
       'No mipmap/filtering changes, image synthesis/upscales, new replacements, transforms, dependency request, commit or push occurred in 099.','']
(root/'outputs/CHECKPOINT-099.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'checkpoint_sha256':sha('outputs/CHECKPOINT-099.md'),'captures_sha256':sha('outputs/RENDERING-099.md'),'goal':'active/incomplete'},indent=2))
