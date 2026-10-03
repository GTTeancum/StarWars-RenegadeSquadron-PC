"""Seal terminal runtime evidence, grouped captures and reproducible state."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent.parent
read=lambda p:json.loads((root/p).read_text())
sha=lambda p:hashlib.file_digest((root/p).open('rb'),'sha256').hexdigest()
c=read('outputs/COVERAGE-103.json');s=read('outputs/TEXTURES-103-state.json')
v=read('outputs/COVERAGE-103-visual.json');m=read('outputs/TEXTURE-MUTABILITY-103.json')
catalog=read('work/texture-catalog103/catalog.json');prior=read('outputs/PRIOR-103-verification.json')
failed=c.get('failed_attempts',[])
assert len(c['runs'])+len(failed)==len(v['runs'])==9
assert all(r['exit_code']==0 and not r['timed_out'] for r in c['runs'])
assert not s['changed_native_sha256']
ordinary=[a for a in catalog['coverage'] if a['archive'].startswith(('ENVS/CLASSIC/','ENVS/PREQUEL/'))]
assert len(ordinary)==34 and all(a['successful_runs_opened'] for a in ordinary)
assert all(next(a for a in catalog['coverage'] if a['archive']==path)['successful_runs_opened'] for path in ['ENVS/GC.AM','ENVS/GC.PSP'])
outcome=read('outputs/CAMPAIGN-103-outcome.json')
assert outcome['terminal_verified'] and outcome['modern_campaign_acceptance'] is False
report=['# Galactic Conquest and campaign checks — checkpoint 103','',
 'Eight menu/GC probes and one bounded legacy campaign attempt are recorded below. Captures from completed runs are real headless 16:9 1280×720 FXAA output. GPU retains 4× MSAA and software reference raster. Any native intermediate campaign images are explicitly labeled 480×272 and were not enlarged.','',
 'Mipmap/filtering work remains skipped. No authored image transforms, new matching, bindings or upscales. Existing source074 remains a partial pack. Menu/terminal success is not campaign victory, modern-control acceptance or original-PSP visual certification.','']
for r in c['runs']:
 name=r['name'];p=f'outputs/{name}-fxaa.png'
 assert sha(p)==c['screenshot_sha256'][p]
 report += [f'## {name}','',v['runs'][name],'',f'![Actual 1280×720 FXAA]({root.as_posix()}/{p})','',f'[Unfiltered render]({root.as_posix()}/outputs/{name}-unfiltered.png)','']
for r in failed:
 report += [f"## {r['name']} — incomplete attempt",'',v['runs'][r['name']],'','No completed final 720p capture is claimed. Terminal logs, original dumps and input/configuration hashes are retained.','']
for p in outcome.get('native_outcome_images',[]):
 report += ['Native software reference (480×272; unchanged pixels):','',f'![Native campaign reference]({root.as_posix()}/{p})','']
(root/'outputs/RENDERING-103.md').write_text('\n'.join(report),encoding='utf-8')
counts=s['counts']
lines=['# Checkpoint 103 — Galactic Conquest and legacy campaign diagnostics','',
 'Status: concrete progress; goal remains active/incomplete. Latest human rendering/manual-matching pivot overrides the older goal wording. Skip item #2 (mipmap/filtering changes). Preserve authored channels/orientation; no automatic matching, new bindings or upscales.','',
 '## Exact changes and revalidation','',
 f"SOURCE-102 and all {prior['verified_source_files']:,} archived source entries/{prior['verified_artifact_files']} receipt artifacts were reverified against current files before work. Prior archive SHA-256 `{prior['source_archive_sha256']}`.",'',
 f"All {s['unchanged_native_source_files']} native source files and executable remain unchanged. All 11 rendering tests last passed in checkpoint100; results/log identities were reverified, not rerun for tool-only changes. Native SHA-256 `{c['native_binary_sha256']}`.",'',
 'Added fresh normal-controller branch probes, completed-capture inspector, bounded historical campaign-recording attempt, scoped 103 catalog/verification tools, grouped report and source snapshot/receipt. No guest position, mission flag, RNG or save-state edits. Root manual guide/browser and TODO refreshed after final verification.','',
 '## Terminal runtime checks','',
 '| Run | Actual expected archive open | Renderer | Stop vblank | Seconds |','| --- | --- | --- | ---: | ---: |']
for r in c['runs']:
 lines.append(f"| {r['name']} | {r['expected_archive'] or 'Campaign menu only'} | {r['renderer']} | {r['stop_vblank']} | {r['elapsed_seconds']:.3f} |")
for r in failed:
 lines.append(f"| {r['name']} — failed attempt | {'; '.join(r['actual_opens']) or 'No environment open recorded'} | GPU requested | requested {r['requested_stop_vblank']}; not reached | {r['elapsed_seconds']:.3f} |")
lines += ['',f"{len(c['runs'])} completed runs reached requested stops with exit 0 and no timeout. {len(failed)} failed bounded attempts are listed separately and are not passing tests. GPU strict/readback is enabled, hardware transform/culling disabled and software reference raster retained. Completed runs report zero backend missing textures. Their real 720p unfiltered/FXAA variants and original decoded textures are preserved. GPU renders HD throughout; software menu probes enable HD near capture. Elapsed times are not comparable performance benchmarks.",'',
 'The GPU feature counters in `COVERAGE-103.json` preserve reported unsupported blend, texture-function and partial color-mask draw counts. Zero in these counters does not prove unreported features or every primitive are supported.','',
 '## Actual visual outcomes','']
lines += [f'- {n}: {finding}' for n,finding in v['runs'].items()]
lines += ['','The fresh Campaign menu offers New and Learn To Play, without Continue. No existing save payload was found in 201 project executable/run/fallback roots before the attempt; this was not a wider user-directory search. Historical checkpoint009 excluded saved profiles, and007 did not verify progress save/reload.','',
 outcome['finding'],'',
 'The long replay uses checkpoint007 legacy PSP input with normal Cross/neutral continuation, not the modern control bridge. Historical Linux victory was not assumed reproduced. Current physical XInput, full first-mission modern controls, later mission traversal and save/reload remain unverified. See `CAMPAIGN-103-outcome.json` for native outcome captures, opens, replay provenance and hashes.','',
 '## Original texture coverage','',
 f"Environment opens: {counts['env_archives_opened']}/47, including all 34 ordinary Classic/Prequel paths and both GC resources. An open is not full traversal, mode/effect coverage or correct visual appearance. The remaining unvisited archive paths are:",'']
lines += [f"- {a['archive']}" for a in catalog['coverage'] if a['archive'].startswith('ENVS/') and not a['successful_runs_opened']]
lines += ['',f"New runs contain {c['texture_ids_in_new_runs']:,} distinct original IDs, {len(c['newly_catalogued_ids'])} absent from frozen 102 and {len(c['newly_runtime_observed_ids'])} newly runtime-observed. Consolidated: {s['merged_original_ids']:,} IDs in {s['merged_image_files']:,} verified PNG/TGA files, {counts['runtime_manifests']} manifests/{counts['runtime_unique_ids']:,} runtime IDs. Static inventory remains 136 Asura containers, 99 texture archives, 4,963 chunks, 12,391 mip occurrences and 2,377 exact archived RGBA identities. No unsupported headers, uncatalogued texture archives, runtime identity or pack errors.",'',
 '| Provenance | IDs |','| --- | ---: |']
lines += [f'| {k} | {n} |' for k,n in counts['status_counts'].items()]
lines += ['',f"Mutable-source audit: {m['case_count']} same-run source configurations/{m['member_ids']} member IDs/{m['render_target_ids_in_cases']} render-target IDs/{m['unresolved_origin_ids_in_cases']} unresolved IDs. Cases are not assets; cross-run addresses do not imply continuity. All originals retained; changing frame captures hidden by default.",'',
 f"All {c['pack074_files_unchanged']} source074 images rehashed unchanged. Original-source indexes copied byte-for-byte from frozen 102; prior095 intake remains 13,820 images in 12 conversion archives, not completely re-audited. Different-alpha runtime IDs remain distinct from named archived RGBA IDs.",'',
 '## Reproducible build and evidence','',
 'Build: `work/build-windows.cmd`; tests: `work/test-rendering.cmd`. Windows x64 Release, retained CMake/Ninja, MSVC 14.44.35207/SDK10.0.26100.0 and `work/windows-sdk`. No missing dependency was proven; no dependency request/download, commit or push.','',
 'Reproduce branch probes with `work/capture-menu103.py` and new immutable run names. Long recording: `work/capture-campaign103.py` (its fixed run/replay name must not be overwritten). Exact per-run inputs/stops/configuration/binary/BOOT are recorded in plan/replay/run.json files. `verify-coverage103.py` verifies terminal/hash/actual-open/capture/original-RGBA evidence. Catalog/audit/browser/test/verification tools ending103 rebuild manual provenance and verify all new manifests. Browser code-level DOM checks passed; no browser visual QA claimed.','',
 'SOURCE-103 ZIP/manifest and independent receipt verify every source entry and final artifacts. Proprietary disc/assets, binaries, dependencies and native run payloads remain excluded from source-only archive and retained locally. Compiler/build/dependency hashes are separately recorded. This is not a fresh-machine build test.','',
 f"- Native SHA-256: `{c['native_binary_sha256']}`",f"- BOOT SHA-256: `{c['boot_sha256']}`"]
for p in ['outputs/PRIOR-103-verification.json','outputs/COVERAGE-103.json','outputs/COVERAGE-103-visual.json','outputs/CAMPAIGN-103-outcome.json','outputs/SAVES-103-inventory.json','outputs/TEXTURES-103-state.json','outputs/TEXTURE-MUTABILITY-103.json','work/texture-catalog103/catalog.json','work/texture-catalog103/index.html','outputs/TEXTURE-103-browser-tests.txt','outputs/RENDERING-103.md']:
 lines.append(f'- {p}: `{sha(p)}`')
lines += ['','## Remaining work','',
 'Unvisited campaign routes, full first-mission modern controls, longer traversal/combat/flight, GC battle/purchases/troop panel, save/reload, every mode/effect/UI/dynamic texture, manual replacement coverage, independent PSP appearance, Space Kashyyyk player fade, CPU framebuffer writes/feedback coherence, guest 16-bit stencil and wider model/material/primitive parity remain incomplete. Mipmap/filtering changes stay skipped.','']
(root/'outputs/CHECKPOINT-103.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'checkpoint_sha256':sha('outputs/CHECKPOINT-103.md'),'render_report_sha256':sha('outputs/RENDERING-103.md'),'goal':'active/incomplete'},indent=2))
