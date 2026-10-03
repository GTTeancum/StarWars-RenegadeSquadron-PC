"""Independently verify terminal movie parity and refreshed original catalog."""
import hashlib,io,json,struct,zipfile
from pathlib import Path
from PIL import Image
import numpy as np
root=Path(__file__).resolve().parent.parent;out=root/'outputs'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
rel=lambda p:p.relative_to(root).as_posix()
run=root/'work/runs/campaign105-movie-parity-gpu';control=root/'work/runs/control-campaign105-movie-parity-gpu'
state=json.loads((run/'run.json').read_text());assert state['state']=='finished' and state['exit_code']==0 and not state['timed_out']
assert state['stop_lines']==['[renegade] STOP: Controller diagnostic stop at 3770 pc=0x8ad2c00 work=0']
native=root/'work/build-windows-native/bin/RenegadeNative.exe'
assert sha(native)==sha(run/'native/RenegadeNative.exe')==state['native_binary_sha256']=='9c6f1e06072ee083fadb17d2cb9b26069d4601747f23590c72128d9110596659'
prior=json.loads((out/'SOURCE-104-manifest.json').read_text());archive=out/'SOURCE-104.zip'
assert sha(archive)==prior['archive_sha256']
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for n,d in prior['source_sha256'].items():assert hashlib.sha256(z.read(n)).hexdigest()==d
old={n:d for n,d in prior['source_sha256'].items() if n.startswith('work/project/source/')}
current={rel(p):sha(p) for p in (root/'work/project/source').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
changed=sorted(n for n,d in old.items() if current.get(n)!=d);added=sorted(current.keys()-old.keys())
assert changed==['work/project/source/profiles/renegade/host/psp_services.cpp','work/project/source/profiles/renegade/tests/dx12_override.cpp']
assert added==['work/project/source/profiles/renegade/host/movie_gpu_present.hpp'] and not old.keys()-current.keys()
assert '100% tests passed out of 11' in (out/'RENDERING-105-build-tests.txt').read_text()
assert 'CPU movie GPU presentation: aspect/channels/stream refresh/GE return passed at1280x720' in (out/'RENDERING-105-test-detail.txt').read_text()
captures={};pairs=0
for p in sorted(control.glob('status_*_vblank_*.json')):
 s=json.loads(p.read_text());assert s['paused'] and s['vblank']==s['until'] and s['gpu_source_vblank']==s['vblank'] and s['gpu_capture']
 captures[rel(p)]=sha(p)
 for field in ['frame','gpu_frame','gpu_fxaa_frame']:
  ppm=control/s[field];png=out/f"campaign105-movie-parity-gpu-{s['sequence']}-{s['vblank']}-{field}.png"
  a=Image.open(ppm);b=Image.open(png);assert a.size==b.size==((480,272) if field=='frame' else (1280,720))
  assert np.array_equal(np.asarray(a),np.asarray(b));captures[rel(ppm)]=sha(ppm);captures[rel(png)]=sha(png);pairs+=1
assert pairs==21
comparisons=[]
for seq,f in [(0,3146),(2,3334)]:
 n=np.asarray(Image.open(out/f'campaign105-movie-parity-gpu-{seq}-{f}-frame.png'));g=np.asarray(Image.open(out/f'campaign105-movie-parity-gpu-{seq}-{f}-gpu_frame.png'))
 scale=min(g.shape[1]/n.shape[1],g.shape[0]/n.shape[0]);left=(g.shape[1]-n.shape[1]*scale)/2;top=(g.shape[0]-n.shape[0]*scale)/2
 xs=np.arange(6,1274);ys=np.arange(1,719);u=np.floor((xs+.5-left)/scale).astype(int);v=np.floor((ys+.5-top)/scale).astype(int)
 ref=n[v[:,None],u[None,:]];actual=g[ys[:,None],xs[None,:]];diff=np.abs(actual.astype(int)-ref.astype(int))
 r=dict(sequence=seq,vblank=f,interior_pixels=int(ref.shape[0]*ref.shape[1]),exact_pixels=int(np.all(diff==0,axis=2).sum()),max_channel_error=int(diff.max()),mean_channel_error=float(diff.mean()),nonblack_pixels=int(np.any(actual!=0,axis=2).sum()),left_bar_max=int(g[:,:4].max()),right_bar_max=int(g[:,1276:].max()))
 assert r['exact_pixels']==r['interior_pixels']==910424 and r['max_channel_error']==r['left_bar_max']==r['right_bar_max']==0
 comparisons.append(r)
assert comparisons==json.loads((out/'MOVIE-105-pixel-comparison.json').read_text())
log=(run/'native.log').read_text(errors='replace');assert '[movie-gpu105] queued vblank=3330' in log
assert not any('[movie-gpu105]' in line and int(line.split('vblank=')[1].split()[0])>=3582 for line in log.splitlines())
catalog=json.loads((root/'work/texture-catalog105/catalog.json').read_text())
assert not any(catalog[k] for k in ['unsupported','runtime_errors','uncatalogued_texture_archives','pack_errors'])
identities={};originals={}
for r in catalog['images']:
 p=root/r['original'];assert sha(p)==r['original_sha256'];data=p.read_bytes()
 im=Image.open(io.BytesIO(data+bytes(max(0,26-len(data))))).convert('RGBA')
 assert 'tex-v1-'+hashlib.sha256(struct.pack('<II',*im.size)+im.tobytes()).hexdigest()==r['id']
 assert im.size==(r['width'],r['height']);identities[r['id']]=r['original_sha256']
for p in (run/'textures').glob('*.tga'):
 assert p.stem in identities;data=p.read_bytes();im=Image.open(io.BytesIO(data+bytes(max(0,26-len(data))))).convert('RGBA')
 assert p.stem=='tex-v1-'+hashlib.sha256(struct.pack('<II',*im.size)+im.tobytes()).hexdigest();originals[rel(p)]=sha(p)
for name in ['campaign104-modern-guided-gpu','campaign105-movie-parity-gpu']:
 assert catalog['runs'][name]['successful_terminal']
 assert catalog['manifest_sha256'][f'work/runs/{name}/textures/textures.jsonl']==sha(root/f'work/runs/{name}/textures/textures.jsonl')
pack=json.loads((out/'TEXTURE-PACK-074.json').read_text())
for r in pack['files']:assert sha(root/r['replacement'])==r['sha256']
assert '"result": "PASS"' in (out/'TEXTURE-105-browser-tests.txt').read_text()
artifacts=[run/'run.json',run/'native.log',control/'commands.log',control/'adaptive105.jsonl',root/'work/texture-catalog105/catalog.json',root/'work/texture-catalog105/index.html',out/'MOVIE-105-pixel-comparison.json',out/'RENDERING-105-build-tests.txt',out/'RENDERING-105-test-detail.txt',out/'RENDERING-105-before-fix-build.txt',out/'TEXTURE-MUTABILITY-105.json']
report=dict(native_binary_sha256=sha(native),native_source_files=len(current),native_source_sha256=current,changed_native=changed,added_native=added,
 stop_vblank=3770,exit_code=0,timed_out=False,lossless_capture_pairs=pairs,movie_comparisons=comparisons,source074_files_unchanged=len(pack['files']),
 original_file_sha256=originals,capture_sha256=captures,catalog_counts=catalog['counts'],artifact_sha256={rel(p):sha(p) for p in artifacts},
 scope='CPU movie display bridge repaired on two actual campaign movie boundaries, subsequent spawn/gameplay view observed. No general CPU framebuffer/feedback parity, full mission, physical controller or all-map visual acceptance. Catalog original pixels verified; code-level browser test, no browser visual QA. Goal updated to dedicated fidelity4x processing; pilot106 in progress, not a completed pack.')
(out/'RENDERING-105-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k in ['native_binary_sha256','native_source_files','lossless_capture_pairs','catalog_counts','source074_files_unchanged']},indent=2))
