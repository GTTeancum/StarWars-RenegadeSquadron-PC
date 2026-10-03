"""Verify actual enhanced-pack loading across five bounded Instant Action routes."""
import hashlib,json,re
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent.parent;sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
pack_path=root/'outputs/TEXTURE-PACK-107.json';pack={r['id']:r for r in json.loads(pack_path.read_text())['files']}
expected={'mygeeto-clone':'ENVS/PREQUEL/MYGEETO.PSP','hoth-gcw':'ENVS/CLASSIC/HOTH.PSP','space-kashyyyk-gcw':'ENVS/CLASSIC/SPACE_KASHYYYK_CIVIL.PSP','geonosis-clone-mode1':'ENVS/PREQUEL/GEONOSIS.PSP','endor-gcw-mode2':'ENVS/CLASSIC/ENDOR.PSP'}
results=[]
for label,archive in expected.items():
 name='textures107-'+label+'-gpu';folder=root/'work/runs'/name;state=json.loads((folder/'run.json').read_text());inspection=json.loads((root/'outputs'/f'{name}-inspection.json').read_text())
 assert state['state']=='finished' and state['exit_code']==0 and not state['timed_out'] and archive in inspection['actual_opens']
 assert state['native_binary_sha256']==sha(folder/'native/RenegadeNative.exe')=='9c6f1e06072ee083fadb17d2cb9b26069d4601747f23590c72128d9110596659'
 env=state['environment'];assert env['RENEGADE_OVERRIDE_ROOT']==str(root/'work/mods-enhanced107') and env['RENEGADE_OUTPUT_RESOLUTION']=='1280x720' and env['RENEGADE_FXAA']=='1' and env['PSPRECOMP_WINDOW']=='0'
 log=(folder/'native.log').read_text(errors='replace');stop=inspection['stop_vblank'];assert f'[gpu-internal-frame] vblank={stop-1} resolution=1280x720' in log
 loaded=sorted(set(re.findall(r'\[overrides\] texture (tex-v1-[0-9a-f]{64}) loaded',log)));assert loaded and all(v in pack for v in loaded)
 enhanced=[v for v in loaded if pack[v].get('effective_method')=='esrgan_x4_detail55'];assert enhanced
 probes=[]
 for line in (folder/'render-report.jsonl').read_text().splitlines():
  for p in json.loads(line)['probes']:
   if p['id'] in pack:
    assert [p['replacement_width'],p['replacement_height']]==pack[p['id']]['output_size'];probes.append(p)
 assert any(p['layer']=='scene' for p in probes) and any(p['layer']=='overlay' for p in probes)
 stats=dict(re.findall(r'(\w+)=([^ ]+)',re.findall(r'\[ge-backend-result\] ([^\r\n]+)',log)[-1]));assert stats['missing_textures']=='0' and int(stats['replacement_draws'])>0
 fxaa=root/'outputs'/f'{name}-fxaa.png';raw=root/'outputs'/f'{name}-unfiltered.png';assert Image.open(fxaa).size==Image.open(raw).size==(1280,720)
 artifacts={p.relative_to(root).as_posix():sha(p) for p in [folder/'run.json',folder/'native.log',folder/'render-report.jsonl',fxaa,raw]}
 results.append(dict(label=label,archive=archive,stop_vblank=stop,loaded_ids=len(loaded),enhanced_loaded_ids=len(enhanced),probe_samples=len(probes),terminal_gpu_stats=stats,artifact_sha256=artifacts))
report=dict(pack_sha256=sha(pack_path),native_binary_sha256='9c6f1e06072ee083fadb17d2cb9b26069d4601747f23590c72128d9110596659',routes=results,scope='Five bounded ground/Clone Wars/GCW/space and mode-index routes. Actual archive opens,720p raw/FXAA captures, scene/overlay replacement dimensions and zero missing textures verified. No full matches, flight, full campaign mission or physical controller acceptance.')
p=root/'outputs/UPSCALER-107-gameplay.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps([{k:r[k] for k in ['label','enhanced_loaded_ids','probe_samples','terminal_gpu_stats']} for r in results],indent=2))
