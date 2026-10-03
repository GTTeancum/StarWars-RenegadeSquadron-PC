"""Audit all refreshed originals and unchanged checkpoint105 native source state."""
import hashlib, io, json, struct
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
catalog_path=root/'work/texture-catalog106/catalog.json';catalog=json.loads(catalog_path.read_text())
assert not any(catalog[k] for k in ['unsupported','uncatalogued_texture_archives','runtime_errors','pack_errors'])
ids={r['id'] for r in catalog['images']};assert len(ids)==len(catalog['images'])==catalog['counts']['catalog_unique_ids']
def identity(p):
 data=p.read_bytes();im=Image.open(io.BytesIO(data+bytes(max(0,26-len(data))))).convert('RGBA')
 return 'tex-v1-'+hashlib.sha256(struct.pack('<II',*im.size)+im.tobytes()).hexdigest()
for r in catalog['images']:
 p=root/r['original'];assert sha(p)==r['original_sha256'] and identity(p)==r['id']
 if r['fallback_override']:assert sha(root/r['fallback_override']['file'])==r['fallback_override']['sha256']
files={};found=set()
for p in (root/'work/texture-dumps-live/textures').iterdir():
 if p.suffix.lower() not in ['.png','.tga']:continue
 assert identity(p)==p.stem and p.stem in ids;found.add(p.stem);files[p.relative_to(root).as_posix()]=sha(p)
assert found==ids
for rel,digest in catalog['manifest_sha256'].items():assert sha(root/rel)==digest
for rel,digest in catalog['render_target_evidence_sha256'].items():assert sha(root/rel)==digest
for scenario in ['mygeeto-clone','hoth-gcw','space-kashyyyk-gcw']:
 for phase in ['before','after-ui2']:
  name=f'textures106-{scenario}-{phase}-gpu';assert catalog['runs'][name]['successful_terminal']
prior=json.loads((root/'outputs/SOURCE-105-manifest.json').read_text())
native_sources={n:d for n,d in prior['source_sha256'].items() if n.startswith('work/project/source/')}
for n,d in native_sources.items():assert sha(root/n)==d
current={p.relative_to(root).as_posix() for p in (root/'work/project/source').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
assert current==native_sources.keys()
binary=sha(root/'work/build-windows-native/bin/RenegadeNative.exe')
assert binary=='9c6f1e06072ee083fadb17d2cb9b26069d4601747f23590c72128d9110596659'
assert '100% tests passed out of 11' in (root/'outputs/RENDERING-105-build-tests.txt').read_text()
pack=json.loads((root/'outputs/TEXTURE-PACK-106-ui2.json').read_text())
assert {r['id'] for r in pack['files']}<=ids
uncovered=[dict(id=r['id'],status=r['status'],original=r['original'],reason='New runtime identity outside immutable105 input plan; retain original and review separately.') for r in catalog['images'] if r['id'] not in {v['id'] for v in pack['files']} and not r['render_target_sample'] and r['status']!='runtime_zero_address']
artifacts=['work/texture-catalog106/catalog.json','work/texture-catalog106/index.html','work/texture-catalog106/textures.csv','work/texture-catalog106/runtime-review.csv','work/texture-catalog106/mutable-sources.csv','outputs/TEXTURE-MUTABILITY-106.json','outputs/TEXTURE-106-browser-tests.txt','outputs/TEXTURE-CATALOG-106.json','outputs/TEXTURE-COVERAGE-106.md','outputs/UPSCALER-106-ui2-verification.json','outputs/UPSCALER-106-gameplay.json']
report=dict(counts=catalog['counts'],merged_original_ids=len(found),merged_original_files=len(files),original_file_sha256=files,
 native_binary_sha256=binary,unchanged_native_source_files=len(native_sources),new_uncovered_non_dynamic=uncovered,
 artifact_sha256={n:sha(root/n) for n in artifacts},
 scope='Every consolidated original identity/hash and final pack binding audited. Native source/binary unchanged from checkpoint105 where all11 rendering tests passed. Browser code-level tests only; no browser visual acceptance. Static archive extraction is complete for retained99 texture archives; runtime/traversal/animation/campaign coverage remains bounded.')
p=root/'outputs/TEXTURES-106-state.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['original_file_sha256','artifact_sha256']},indent=2))
