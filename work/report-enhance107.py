"""Create checkpoint107 reports and grouped clean/enhanced comparisons."""
import hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parent.parent;out=root/'outputs';sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
pack=json.loads((out/'TEXTURE-PACK-107.json').read_text());verify=json.loads((out/'UPSCALER-107-verification.json').read_text());game=json.loads((out/'UPSCALER-107-gameplay.json').read_text());state=json.loads((out/'TEXTURES-107-state.json').read_text());review=json.loads((out/'UPSCALER-107-raw-review.json').read_text())
assert not state['new_uncovered_non_dynamic'] and game['pack_sha256']==sha(out/'TEXTURE-PACK-107.json') and verify['exact_weight']==.55
counts=state['counts'];lines=['# Checkpoint 107 — visible 55% ESRGAN texture enhancement','',
 'Checkpoint 106 was correctly rejected by the user as cleanup rather than meaningful enhancement. Checkpoint 107 deploys the user-selected 55% ESRGAN detail layer on 1,827 eligible non-UI textures, retaining 45% of the clean checkpoint-106 RGB. This materially raises microstructure and edge contrast. ESRGAN reconstructs plausible detail; it cannot recover unknown original authored detail.','',
 'The 1,827-image batch completed all 29 chunks. Every intermediate hash and dimension passed. The final independent audit recomputed each 55% blend byte-for-byte. The remaining 741 images are byte-identical to checkpoint106: 355 verified authored-source replacements plus exact UI/text, fidelity-rejected, transparent and other preserved cases. Generated alpha remains exact source replication. No channel/orientation, mipmap or filtering change.','',
 'The pilot rejected full RealESRGAN as too smooth and full ESRGAN as too grainy. The selected 55% hybrid was reviewed on brick, stone, wall, grass, snow and a trooper atlas before the full run. Final review adds pilot samples, deterministic samples from every category and the highest high-frequency changes. This is representative artistic QA, not certification of every invented feature.','',
 f'Native binary remains `{game["native_binary_sha256"]}` and native source is unchanged from checkpoint105. Checkpoint107 reran the rendering suite: all 11 tests passed. The pack changes data only.','',
 '| Scenario | Actual archive | Stop | Enhanced IDs loaded | Result |','| --- | --- | ---: | ---: | --- |']
for r in game['routes']:lines.append(f"| {r['label']} | {r['archive']} | {r['stop_vblank']} | {r['enhanced_loaded_ids']} | exit 0, no timeout, missing textures 0 |")
lines+=['','All five runs used actual 1280×720 DirectX12 rendering, 4× MSAA, FXAA, modern/XInput configuration and original dumping. Scene and overlay replacement dimensions were checked against the pack. These are bounded Instant Action routes spanning Clone Wars, GCW, ground, space and two additional mode indices. They do not prove full matches, flight, campaign completion, save/reload or physical-controller acceptance.','',
 f'The refreshed catalog verifies {counts["catalog_unique_ids"]} original IDs from all {counts["texture_archives"]} retained texture archives and {counts["runtime_manifests"]} runtime manifests. {counts["render_target_sample_ids"]} changing render-target samples remain original and excluded from permanent replacement. Environment archive opens remain {counts["env_archives_opened"]}/47; an open does not prove traversal. No new non-dynamic ID was found outside pack107.','',
 'Launch `Play-Upscaled-Textures.cmd`. Replace any result in `work/mods-enhanced107/textures` using its original content-ID basename; DDS, TGA and PNG remain supported. The 355 authored source replacements keep priority. The previous clean pack remains in `work/mods-upscale106-ui2`.','',
 'Remaining project work includes full first-mission completion/save/reload, flight and full-match traversal, independent PSP visual references, broader GPU/CPU framebuffer parity, and model/material validation.','', 'Verified artifacts:']
for n in ['outputs/TEXTURE-PACK-107.json','outputs/UPSCALER-107-verification.json','outputs/UPSCALER-107-gameplay.json','outputs/UPSCALER-107-raw-review.json','outputs/TEXTURES-107-state.json','outputs/RENDERING-107-build-tests.txt','outputs/UPSCALER-107-plan.json','work/upscale107/batch/run.json','Play-Upscaled-Textures.cmd']:
 lines.append(f'- {n}: `{sha(root/n)}`')
(out/'CHECKPOINT-107.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
render=['# Rendering comparison — checkpoint 107','',
 'Left: corrected clean checkpoint106. Right: user-selected55% ESRGAN detail checkpoint107. Both use the same native binary, 1280×720 GPU path, 4× MSAA and FXAA. Fresh runs reuse the same controller routes and boundaries, but actor timing is not deterministic; scene pixel differences are supporting evidence rather than pure texture-only attribution. Raw texture sheets are the direct enhancement comparison.','']
for scenario in ['mygeeto-clone','hoth-gcw','space-kashyyyk-gcw']:
 before=out/f'textures106-{scenario}-after-ui2-gpu-fxaa.png';after=out/f'textures107-{scenario}-gpu-fxaa.png';pair=Image.new('RGB',(2560,744),(25,25,25));draw=ImageDraw.Draw(pair);draw.text((8,6),'Clean106',fill='white');draw.text((1288,6),'Enhanced107: 55% ESRGAN detail',fill='white');pair.paste(Image.open(before),(0,24));pair.paste(Image.open(after),(1280,24));dest=out/f'UPSCALER-107-{scenario}-comparison.png';pair.save(dest)
 render += [f'## {scenario}','',f'![Clean versus enhanced]({dest.as_posix()})','']
for scenario in ['geonosis-clone-mode1','endor-gcw-mode2']:
 render += [f'## {scenario}','',f'![Enhanced checkpoint107]({(out/f"textures107-{scenario}-gpu-fxaa.png").as_posix()})','']
render += ['## Raw texture comparisons','',f'![Selected 55 percent pilot]({(out/"UPSCALER-107-hybrid-comparison.png").as_posix()})','']
for page in review['pages']:render += [f'![Full-pack representative review]({(root/page["file"]).as_posix()})','']
render += [f'![Largest environment detail ratios]({(root/review["environment_outliers"]["file"]).as_posix()})','']
render += ['The 55% pass is intentionally sharper and more textured than checkpoint106. Full ESRGAN was rejected because it produced excessive grain; the retained 45% clean RGB moderates it. UI/text and authored-source images are unchanged. High-frequency ranking helps expose aggressive cases but does not prove semantic correctness.']
(out/'RENDERING-107.md').write_text('\n'.join(render)+'\n',encoding='utf-8');print('Checkpoint107 and grouped report written')
