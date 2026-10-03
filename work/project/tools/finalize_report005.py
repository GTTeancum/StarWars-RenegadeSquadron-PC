#!/usr/bin/env python3
"""Record observed checkpoint-005 evidence; does not infer gameplay from exit status."""
from pathlib import Path
import datetime,hashlib,json,re
from PIL import Image
r=Path('/mnt/data/renegade'); e=r/'evidence005'; logs=r/'logs/session005'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
binary=r/'intake/out/native004/bin/RenegadeNative'; independent=r/'independent005/final-build/bin/RenegadeNative'
h=sha(binary)
assert h=='f0b2dd0f99a30aa83d78ef103b76403331e84b9b7cb4dec2cb355ffbbaa6a275'
assert sha(independent)==h
runs=[]
for p in sorted((r/'runs').glob('*005*/run.json')):
    d=json.loads(p.read_text());assert d['state']=='finished',p
    runs.append({'name':p.parent.name,**d})
negative=json.loads((logs/'negative/results.json').read_text())
assert negative['passed'] and len(negative['cases'])==9 and negative['binary_sha256']==h
assert '100% tests passed, 0 tests failed out of 10' in (logs/'tests005-release-verbose.log').read_text()
assert '100% tests passed, 0 tests failed out of 10' in (logs/'independent-final-build.log').read_text()
images=[]
for name,scope in [
 ('final-resolution-selector-flight-3x.png','Actual SDL/X11 window, title bar and functional dropdown, over powered flight'),
 ('final-native-flight-3x.png','Actual SDL/X11 window over powered flight'),
 ('native005-final-repeat-3150-2x.png','Direct final-binary recon-droid kill framebuffer, 2x nearest-neighbor'),
 ('final-cold-jetpack-5429-2x.png','Direct final-binary powered-flight framebuffer, 2x nearest-neighbor'),
 ('final-damaged-profile-2x.png','Actual final-binary host presentation of damaged-profile system dialog'),
 ('final-corrupt-load-failed-2x.png','Original game Load Failed screen after explicit dismissal'),
 ('final-corrupt-returned-to-menu-2x.png','Original game profile menu after error and Back')]:
    p=e/name
    with Image.open(p) as im: size=im.size
    assert size[0]>=960 and size[1]>=544
    images.append({'path':'evidence/'+name,'width':size[0],'height':size[1],'sha256':sha(p),'native_binary_sha256':h,'scope':scope})
summary={
 'format':'renegade-smoke-005-v1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'final_native_binary_sha256':h,'independent_binary_sha256':sha(independent),
 'first_level_completion_verified':False,'windows_verified':False,'internal_render_dimensions':[480,272],
 'ctest_targets_passed':10,'negative_executable_scenarios_passed':9,'checkpoint_verifier_synthetic_tests_passed':14,
 'final_cold_replay':{'run':'native005-final-repeat','reached_virtual_vblank':5429,'replay':'replays/yavin-jetpack-flight005.txt',
 'controller_intervals':129,'pause_free_until_endpoint':True,
 'visually_verified_outcomes':['Yavin IV spawn','movement tutorial','recon-droid destruction','pause/audio-options navigation','command-post capture','jetpack selection','powered jetpack flight'],
 'end_reason':'Actual OS window close while diagnostic-paused after reaching 5429; not level completion',
 'real_time_performance_claim':False,'bit_exact_repeatability_claim':False},
 'save_scope':'A new profile saved and loaded in a separate process on the pre-dialog 2d29 build; final f0b2 repeated the damaged-save rejection and menu recovery. No campaign-progress save/reload certification.',
 'corrupt_save_scope':'One-byte copy in an isolated fixture; original assets and valid save not changed; system error 0x80110306 needs explicit Circle dismissal; Cross alone did not dismiss.',
 'screenshots':images,'runs':runs,'negative_executable_checks':negative,
 'limitations':['Tank destruction and first-level victory unverified','Full campaign and other maps unverified','No Windows build/toolkit','No physical controller or high-DPI certification','Complete audio correctness unverified','Higher output sizes do not increase internal rendering detail','No real-time benchmark','No bit-identical whole-game determinism','Custom V3 dialog labels and non-ASCII encodings rejected']}
(e/'smoke-results005.json').write_text(json.dumps(summary,indent=2)+'\n')
(r/'README-005.md').write_text((r/'README-005.md').read_text().replace('See the newest CHECKPOINT-005*.md','See CHECKPOINT-005.md (the final report; 005A-005E are intermediate notes)').replace('replays/yavin-jetpack-equipped004.txt','replays/yavin-jetpack-flight005.txt').replace('--vblanks 4934 --timeout 900 --start 3000 --stride 15','--vblanks 5430 --timeout 900 --start 2400 --stride 30'))
report=f'''# Renegade Squadron — native checkpoint 005

Final report, {summary['created_utc']}. Supersedes the pending statuses in intermediate notes 005A–005E, which remain as a timestamped engineering history.

**Implemented and tested:** a working output-resolution selector below the OS title bar; native cold-boot progression through recon combat, command-post capture and powered jetpack flight; new-profile save/load smoke coverage; a newly implemented system-message path that reports a damaged save and returns safely to the menu. **First-level victory and Windows compatibility are not signed off.**

## Source and build identity

Final native executable SHA-256:

```
{h}
```

The independent fresh framework/host/services build from the separately staged current source produced the exact same executable hash and passed all ten CTest targets. Both builds link the previously compiled Linux x86-64 AOT archive after verifying its hash and 414 generated-source/core-header records. This is not a fresh compilation of every generated game translation unit and is not a Windows build. No source changes were made after this final build; later changes are reports and packaging tools only.

Upstream PSPRecomp commit: `f6e7d415c7f447b934cc3865a31eb725f353d659`.
BOOT.BIN SHA-256: `f4c7a9ef93475fc8017f649346ef79b599649dc47462ec419e9fd373146f8c68`.
Original ISO SHA-256: `92d2da6c0a0a689ef5d04475a3c63b80d8e86d6bc4688dbde4adb06b24220326`.

## Output selector and genuine screenshots

The SDL client now contains a 40-pixel toolbar immediately below the OS title bar. Its dropdown offers **480×272, 960×544, 1440×816, 1920×1088, 1280×720 and 1920×1080** picture-area sizes. The default is 960×544 (2×). Mouse clicks or Alt+R, Up/Down and Enter select a size. Escape closes an open dropdown before closing the application. Maximized windows restore before applying a preset. Arbitrary manual resizing preserves aspect ratio and displays CUSTOM.

These are presentation/output sizes, **not increased internal rendering resolution**. The software-rendered guest image remains 480×272, with nearest-neighbor scaling and aspect-preserving sidebars as needed. The toolbar height is additional to the chosen picture area. Settings last for the current process; persistent display settings are not claimed.

GUI interaction is isolated from PSP controls; input becomes neutral while the menu is open or the window is unfocused. SDL event handling remains responsive while diagnostics hold the guest clock paused. The previously separate 004G guest-clock isolation fix is integrated, so host pacing and diagnostic pauses do not add wall-clock lateness to virtual time.

Actual X11 mouse/keyboard tests selected 2×, 3× and 720p over the native game, opened/closed the dropdown, resized and restored a maximized window, changed focus and closed the native application during a diagnostic pause. Synthetic production-SDL tests cover all six presets, aspect/viewport geometry, selected-state pixels, input isolation, invalid settings and modal presentation. This is normal-DPI Xvfb/software-SDL testing, not physical-controller, high-DPI or Windows certification.

The final screenshots in `evidence/smoke-results005.json` are bound to the final binary. The live-window captures include actual OS decorations and toolbar; direct guest captures are enlarged 2× without adding detail. No scene is generated or enhanced. The step helper defaults to 2× PNG exports while preserving raw 480×272 PPMs. No font files are included.

## Actual native smoke scenarios

| Scenario | Verified result and boundary |
|---|---|
| Final cold campaign/control replay | `native005-final-repeat`, final executable: normal menus, Campaign/New, movie skip, Yavin spawn, movement tutorial, recon-droid kill, pause/audio-options navigation, Rebel Base command-post capture, equipment/jetpack selection and powered flight. It reaches VBlank 5429 without diagnostic pauses before that endpoint. |
| Final termination/UI | At the 5429 diagnostic pause the live dropdown still worked; closing the actual OS window stopped normally. Exit 0, no timeout, 101 automatic frame captures. The runner's 457.003 wall seconds includes concurrent work and endpoint UI inspection, so it is not a real-time benchmark. |
| Independent earlier cold replay | `native005-clean-repeat`, earlier selector/identity binary `2d29…`: separate rebuilt executable cold-boots through recon destruction at VBlank 3162, exit 0, no timeout. Its evidence is not mislabeled as final `f0b2…` evidence. |
| Presentation variants | Earlier windowed, headless paced and single-worker unpaced runs all reached inspected recon-combat outcomes. Pixel differences existed between these variants; no whole-game bit determinism or controlled performance comparison is claimed. |
| Profile persistence | `native005-save` and `native005-reload` on `2d29…`: a new profile displays Profile Saved, creates a 16,384-byte DATA.BIN and ICON0.PNG, then a fresh native process displays Load Successful. This verifies a new-profile round trip, not in-mission/campaign-progress saves. |
| Missing profile | `native005-missing-save` on `2d29…`: loading from an empty isolated save directory displays Load Failed and returns a normal diagnostic stop. |
| Damaged profile, before repair | `native005-corrupt-save` on `2d29…`: a separate one-byte copy exposes a real missing `sceUtilityMsgDialogInitStart` import, exits 4, and is preserved as a failed test. |
| Damaged profile, final repair | `native005-final-corrupt`, final executable: visible host system message reports 0x80110306. Cross alone does not dismiss this cancel-only dialog. Circle explicitly returns to the game's Load Failed screen, then Back returns to the actual profile menu. Exit 0, no timeout; damaged bytes remain unchanged and the original valid profile is untouched. |
| Invalid startup | Nine actual final-executable runs correctly reject missing/empty/modified BOOT, wrong disc root, malformed/negative/zero dispatch budgets, invalid resolution and invalid scale. Each checks the expected diagnostic, not just nonzero exit. |

The 129-interval `replays/yavin-jetpack-flight005.txt` records the legitimate controller-only route. The final replay reproduces the important outcomes reached interactively earlier in this turn. It does not write player coordinates, health, inventory, mission state or save-state contents. The comparison of the earlier and final guest frame at 5429 differs in 619 of 130,560 pixels, so the report claims observed outcome repeatability, **not bit-identical replay**. The old 004 equipment tape diverged after the clock correction and is retained only as historical input.

## Reverse-engineering fix uncovered by smoke testing

The damaged-save test reached an unimplemented PSP system-dialog import at PC 0x08AD2980. Implemented the bounded message-dialog init, status, update, shutdown and abort services. Guest parameter variants of 572, 580 and 708 bytes are validated before access; lifecycle transitions and result writeback are explicit. Input release/edges prevent a held confirm button from auto-acknowledging a new dialog. Savedata and message utilities cannot run concurrently. Yes/No/default-No/cancel-disabled and bounded scrolling paths are covered in synthetic production-HLE tests.

The actual game requests the 580-byte numeric-error variant with mode 0, options 0 and error 0x80110306. The host displays the damaged-profile message and exact code over presentation; it does not modify the guest framebuffer, repair the save, or pretend that loading succeeded. Unsupported flags, variants, non-ASCII strings and custom V3 button labels are rejected. Full PSP firmware fonts, dialog sounds, all locales and exact firmware timing are outside this implementation's verified scope.

Also hardened native entry validation: the AOT executable requires the exact expected BOOT hash/size, validated disc identity and data root, valid positive dispatch budget, and no invalid or unsupported ELF relocation results. This prevents accidentally dispatching the fixed AOT code against the wrong executable.

## Regression and recovery evidence

**10/10 CTest targets pass** on the final working build and independent source-staged host/core/services build. Focused check counts: core/VFPU/scratchpad/GE transfer 50,958; platform 103; asset-dependent PSMF/platform 280; scheduler 36; ATRAC bounds/terminal behavior 48; stencil 15,158; clock 213; display/resolution/input/pixels 7,833,891; message lifecycle/ABI/input 1,580. The display count includes per-pixel comparisons, not millions of different play scenarios. The remaining CTest target is the upstream framework pipeline.

Nine negative executable checks pass; fourteen synthetic checkpoint/AOT verification accept/reject tests pass. Logs preserve an intermediate message-test fixture failure and the actual missing-import failure rather than presenting only successful tests. The final source snapshot includes both the clock and message-dialog fixes.

Key evidence: `evidence/logs/tests005-release-verbose.log`, `evidence/logs/independent-final-build.log`, `evidence/logs/negative/results.json`, `evidence/logs/recovery-verifier-tests.log`, `evidence/smoke-results005.json`, each `evidence/runs/*/run.json` with exact binary hash/environment/termination, actual controller records, screenshots and `evidence/final-flight-comparison.json`.

## Remaining acceptance gates

Tank destruction, remaining first-level objectives and the victory transition still need a native completion run and repeat. Earlier 004E combat/death/respawn/turret observations are not silently upgraded into newly repeated final-build results. Full campaign coverage, other maps, mission-progress save/reload, complete audio correctness, real-time performance, physical-controller/high-DPI coverage and Windows compatibility remain unverified. No completed mission, completed port or Windows toolkit is claimed.

## Preservation

The cumulative 005 ZIP contains the current source, source-bound saved AOT archive, final Linux executable, build/recovery helpers, current and historical Markdown checkpoints, replays, source hashes, logs, run statuses and genuine screenshots. It excludes original game assets/executables, PRX, ISO, saved profiles, RAM/VRAM dumps, font files, build caches and intermediate objects. The user's original game/intake remain sufficient; no collector rerun is required. Use the included README and verified full source rather than reapplying historical patch scripts.

The packager verifies the complete ZIP CRCs and manifest hashes before publishing it and writes an external SHA-256 sidecar. Independent source-to-ZIP equivalence is recorded separately after packaging, without modifying the sealed archive.
'''
(r/'CHECKPOINT-005.md').write_text(report)
print('Final report and smoke results recorded:',h,len(runs),'native runs')
