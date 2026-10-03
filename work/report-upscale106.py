"""Write final milestone documentation from completed independent receipts."""
import hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parent.parent;out=root/'outputs'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
pack=json.loads((out/'TEXTURE-PACK-106-ui2.json').read_text())
verified=json.loads((out/'UPSCALER-106-ui2-verification.json').read_text())
game=json.loads((out/'UPSCALER-106-gameplay.json').read_text())
state=json.loads((out/'TEXTURES-106-state.json').read_text())
assert not state['new_uncovered_non_dynamic'],'Review new runtime identities before final acceptance'
assert game['pack_sha256']==sha(out/'TEXTURE-PACK-106-ui2.json')
native=state['native_binary_sha256'];counts=state['counts']
lines=['# Checkpoint106 — fidelity 4× pack and representative 720p validation','',
 'Completed corrected texture pack: 2,568 original content identities deployed. 355 verified authored-source images and sidecars remain byte-identical and preferred. 2,213 generated images are 4× in each dimension with exact integer-replicated source alpha. Original orientation/channels retained; no new source matching, model bindings, mipmap or filtering changes.','',
 'The dedicated native RealESRNet batch produced 1,906 RGB intermediates in 30 successful chunks (2828.049 seconds). Conservative final RGB blends limit neural contribution to 50% and reduce it for excessive source-sized reconstruction drift. Final methods: 1,827 blends; 307 initial integer cases; 46 corrected UI cases; 17 fidelity rejections; 16 fully transparent exact-preservation cases; 355 preferred authored replacements. Numerical bounds and 16 visual samples do not certify every artistic feature.','',
 'Visual review caught a GUI path delimiter bug in the immutable initial preparation plan. A separate UI2 pack fixes 46 menu/UI images to exact scaling using normalized name/archive paths. The initial plan, intermediates, first candidate, independent first audit and first-candidate Mygeeto run remain retained. No accepted outputs were silently overwritten. The final launcher uses UI2.','',
 'Every final image was independently checked: original content identity/source hash, output hash/dimensions, generated alpha, integer RGBA cases, one image provider perID, authored source/sidecar precedence, and bounded source reconstruction. The launcher dry run verifies1280×720 DirectX12 preview, FXAA, modern/XInput controls and original dumping.','',
 f'Native binary unchanged: `{native}`. All {state["unchanged_native_source_files"]} native source files remain identical to SOURCE105. The 11 rendering tests passed at105; they were not repeated for this texture/tool-only milestone. The105 movie presentation repair and104 modern first-mission progress remain retained; no new full-mission completion is claimed.','',
 '| Scenario | Stop | Result | Generated loaded IDs | Authored loaded IDs |','| --- | ---: | --- | ---: | ---: |']
for r in game['scenarios']:
 lines.append(f"| {r['scenario']} | {r['stop_vblank']} | exit0, no timeout, missing textures0 | {r['generated_loaded']} | {r['authored_loaded']} |")
lines+=['','Actual archive opens, unchanged replay/native/boot and capture boundaries were checked. Scene probes 128×128→512×512 and overlay probes 256×256→1024×1024 establish actual replacement use. Raw and FXAA captures are real 1280×720 renders, encoded losslessly. Independent game timing/actors can differ between fresh runs; screen differences are not pure texture-only pixel comparisons. These are bounded spawn views, not completed matches/flight or all-map visual acceptance.','',
 f'Original catalog: {counts["catalog_unique_ids"]} contentIDs, {counts["runtime_manifests"]} runtime manifests, {counts["runtime_only_ids"]} runtime-only IDs, {counts["render_target_sample_ids"]} observed render-target samples. Static extraction verified all 99 retained texture archives (136 Asura containers, 4,963 texture chunks, 12,391 mip occurrences). Environment opens remain {counts["env_archives_opened"]}/47; all 34 ordinary Classic/Prequel paths are retained, but ten Campaign paths remain unopened. An archive open is not full traversal.','',
 'The immutable105 input plan excluded 1,554 render-target/zero-address samples from permanent replacement, retaining their originals. New sampled-frame identities added by these runs stay cataloged and excluded; no new uncovered non-dynamic identity was found. Source095 conversion intake records 13,820 originals from 12 archives;106 copies the independently hash-checked102 source index without a new exhaustive intake audit. No automatic ambiguous matches were accepted.','',
 'Catalog/browser now show final fallback filename, processing method and dimensions alongside original/name/archive provenance. Code-level filter/pagination/filename/provenance tests passed; no browser visual acceptance is claimed. The106 tools write isolated numbered outputs, correcting inherited103 output names in the105 catalog script.','',
 'Launch `Play-Upscaled-Textures.cmd`; edit `work/mods-upscale106-ui2/textures` using original content-ID names. See UPSCALED-TEXTURES.md. Source-only SOURCE106 records the exact local tool/build/dependency identities; proprietary images/disc data, model/tool binaries and generated assets remain separate. This is not a fresh-machine restoration test. No commit/push in this milestone.','',
 'Reproduction order: prepare-upscale106 → run-upscale106 → check-upscale106 → finalize-upscale106 → verify-upscale106 → correct-ui-upscale106 → verify-upscale106 --ui2 → fresh capture/inspection routes → verify-gameplay106 → refresh-catalog106 → report-upscale106 → snapshot-source106 → receipt-source106. Completed batch/run names are immutable; reuse their receipts instead of starting duplicate jobs.','',
 'Larger-project work still open: full first mission/save/reload, physical-controller play, flight/full match traversal, independent PSP visual references, general CPU framebuffer/feedback and broader GPU/model/material parity. The current texture milestone does not imply those are complete.','', 'Verified artifacts:']
for n in ['outputs/TEXTURE-PACK-106-ui2.json','outputs/UPSCALER-106-ui2-verification.json','outputs/UPSCALER-106-gameplay.json','outputs/TEXTURES-106-state.json','work/texture-catalog106/catalog.json','outputs/UPSCALER-106-plan.json','work/correct-ui-upscale106.py','work/verify-upscale106.py','Play-Upscaled-Textures.cmd']:
 lines.append(f'- {n}: `{sha(root/n)}`')
(out/'CHECKPOINT-106.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
visual=['# Grouped rendering comparison — checkpoint106','',
 'Each pair uses the same native build, controller replay and capture boundary. Left:existing source074 pack. Right:corrected 4× fallback pack with source074 preferred. Both actual1280x720 GPU 4×MSAA with FXAA and no filter/mipmap changes. Timing/actors are not forced identical; larger image dimensions and successful load/probe receipts establish replacement use.','']
for r in game['scenarios']:
 scenario=r['scenario'];before=out/f'textures106-{scenario}-before-gpu-fxaa.png';after=out/f'textures106-{scenario}-after-ui2-gpu-fxaa.png'
 pair=Image.new('RGB',(2560,744),(25,25,25));draw=ImageDraw.Draw(pair)
 draw.text((8,6),'Before: source074 preferred',fill='white');draw.text((1288,6),'After: corrected fidelity4x + source074 preferred',fill='white')
 pair.paste(Image.open(before),(0,24));pair.paste(Image.open(after),(1280,24))
 dest=out/f'UPSCALER-106-{scenario}-comparison.png';pair.save(dest)
 visual += [f'## {scenario}','',f'![Before and after]({dest.as_posix()})','',f'[Original before720p PNG]({before.as_posix()}) · [Final after720p PNG]({after.as_posix()})','']
visual+=['## Representative asset review','',
 'Sixteen source/final samples include the pilot subjects, largest retained reconstruction differences, rejected cases and partial-alpha textures. The limited blend retains visible stone relief/grain and line/silhouette layout; alpha edges remain original. Fonts/icons retain source glyph pixels; they are not newly drawn or claimed to contain recovered detail. UI review corrected 46 atlases. Full-pack automated checks are separate from representative artistic review.','',
 f'![Pilot samples]({(out/"UPSCALER-106-final-pilot-qa.png").as_posix()})','',
 f'![Stress samples]({(out/"UPSCALER-106-final-stress-qa.png").as_posix()})','',
 'Existing Hoth fog/snow distance appearance, large foreground Mygeeto objective marker and other PSP/GPU parity questions remain outside texture-pack acceptance. These views do not establish independent original-PSP correctness. Earlier movie repair and guided first-mission captures are grouped in RENDERING105.md and RENDERING104.md.']
(out/'RENDERING-106.md').write_text('\n'.join(visual)+'\n',encoding='utf-8')
print('Final checkpoint and grouped rendering report written')
