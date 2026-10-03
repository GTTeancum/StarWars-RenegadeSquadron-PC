"""Verify consolidated original pixels, links and unchanged tested renderer state."""
import hashlib, io, json, struct
from pathlib import Path
from PIL import Image
root = Path(__file__).resolve().parent.parent
sha = lambda p: hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
catalog = json.loads((root / 'work/texture-catalog103/catalog.json').read_text())
ids = {r['id'] for r in catalog['images']}
assert len(ids) == len(catalog['images']) == catalog['counts']['catalog_unique_ids']
coverage=json.loads((root/'outputs/COVERAGE-103.json').read_text())
for run in coverage['runs']+coverage.get('failed_attempts',[]):
    name=run['name']
    manifest_name=f'work/runs/{name}/textures/textures.jsonl'
    assert catalog['manifest_sha256'][manifest_name]==sha(root/manifest_name),name
    assert catalog['runs'][name]['successful_terminal'] == (run in coverage['runs']),name
    assert catalog['runs'][name]['state_sha256']==sha(root/f'work/runs/{name}/run.json'),name
    for path in run['original_file_sha256']:
        assert Path(path).stem in ids,name
folder = root / 'work/texture-dumps-live/textures'
found, files = set(), {}
for p in sorted(folder.iterdir()):
    if p.suffix.lower() not in {'.png', '.tga'}:
        continue
    data = p.read_bytes()
    if p.suffix.lower() == '.tga' and len(data) < 26:
        data += bytes(26 - len(data))
    im = Image.open(io.BytesIO(data)).convert('RGBA')
    id_ = 'tex-v1-' + hashlib.sha256(struct.pack('<II', *im.size) + im.tobytes()).hexdigest()
    assert p.stem == id_ and id_ in ids, p
    found.add(id_)
    files[p.relative_to(root).as_posix()] = sha(p)
assert found == ids, f'Missing consolidated originals: {sorted(ids-found)}'
for row in catalog['images']:
    assert sha(root / row['original']) == row['original_sha256'], row['id']
manifest = json.loads((root / 'outputs/SOURCE-102-manifest.json').read_text())
prior_receipt=json.loads((root/'outputs/SOURCE-102-receipt.json').read_text())
prior_state=json.loads((root/'outputs/TEXTURES-102-state.json').read_text())
for name in ['outputs/SOURCE-102-manifest.json','outputs/TEXTURES-102-state.json']:
    assert sha(root/name)==prior_receipt['artifact_sha256'][name],name
for name,digest in prior_state['artifact_sha256'].items():
    if name.startswith('outputs/FOG-100-'):
        assert sha(root/name)==digest,name
cpp = ['work/project/source/profiles/vcs/host/ge_renderer.cpp',
       'work/project/source/profiles/vcs/host/ge_gpu_backend_dx12.cpp',
       'work/project/source/profiles/vcs/host/ge_gpu_backend.hpp',
       'work/project/source/profiles/renegade/host/display_sdl.cpp',
       'work/project/source/profiles/renegade/host/main.cpp',
       'work/project/source/profiles/renegade/host/psp_services.cpp']
native_sources = {name:digest for name,digest in manifest['source_sha256'].items()
                  if name.startswith('work/project/source/')}
changed_native=set()
for name,digest in native_sources.items():
    assert sha(root/name)==digest,name
new_native={p.relative_to(root).as_posix() for p in (root/'work/project/source').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
assert new_native==native_sources.keys(),'Native source inventory changed unexpectedly'
final_tests=(root/'outputs/FOG-100-final-build-tests.txt').read_text()
assert '100% tests passed out of 11' in final_tests
detail=(root/'outputs/FOG-100-test-detail.txt').read_text()
assert 'HD boundary samples 0 51 153 255' in detail
assert 'HD unequal-W sample 85' in detail and 'GPU unequal-W sample 85' in detail
assert 'Native boundary samples 255 255 255 255' in (root/'outputs/FOG-100-before-test.txt').read_text()
for name,digest in catalog['render_target_evidence_sha256'].items():
    assert sha(root/name) == digest, name
assert sum(row['render_target_sample'] for row in catalog['images']) >= 798
for row in catalog['images']:
    assert row['render_target_sample'] == bool(row['render_target_records']), row['id']
    for record in row['render_target_records']:
        assert record['run'] and (record['address'] & 0x3f000000) == 0x04000000
        assert record['format'] == 3 and not record['swizzled']
        assert record['width'] == record['height'] == record['buffer_width'] == 512
binary = sha(root / 'work/build-windows-native/bin/RenegadeNative.exe')
assert binary == '924ae90a2ed8141bb418df07203100912bb08176eb987b3a834819a49a68e2ec'
sources = json.loads((root / 'outputs/TEXTURE-SOURCES-095.json').read_text())
assert not sources['failures'] and sources['image_count'] == 13820 and len(sources['archives']) == 12
assert not any(catalog[k] for k in ['unsupported','uncatalogued_texture_archives','runtime_errors','pack_errors'])
artifacts = ['outputs/CAMPAIGN-103-outcome.json', 'outputs/SAVES-103-inventory.json', 'outputs/PRIOR-103-verification.json', 'work/texture-catalog103/catalog.json', 'work/texture-catalog103/index.html',
             'work/texture-catalog103/textures.csv', 'work/texture-catalog103/runtime-review.csv',
             'work/texture-catalog103/original-sources.csv', 'work/texture-catalog103/original-sources.json', 'outputs/COVERAGE-103.json', 'outputs/COVERAGE-103-visual.json', 'outputs/TEXTURE-MUTABILITY-103.json', 'work/texture-catalog103/mutable-sources.csv', 'outputs/FOG-100-final-build-tests.txt', 'outputs/FOG-100-before-test.txt', 'outputs/FOG-100-test-detail.txt', 'outputs/FOG-100-build-tests.txt', 'outputs/FOG-100-cache-build-tests.txt',
             'outputs/TEXTURE-CATALOG-103.json', 'outputs/TEXTURE-COVERAGE-103.md',
             'outputs/TEXTURE-SOURCES-095.json', 'outputs/TEXTURE-103-browser-tests.txt']
report = dict(counts=catalog['counts'], merged_original_ids=len(found), merged_image_files=len(files),
              original_file_sha256=files, artifact_sha256={name:sha(root/name) for name in artifacts},
              renderer_sha256={name:sha(root/name) for name in cpp}, unchanged_native_source_files=len(native_sources)-len(changed_native),
              changed_native_sha256={name:sha(root/name) for name in sorted(changed_native)}, native_binary_sha256=binary,
              sources=sources, renderer_validation='Native sources and binary rehashed unchanged from verified SOURCE-102. All 11 rendering tests passed in checkpoint 100; not repeated for tool-only 103 changes. GC/menu and bounded legacy-campaign runtime evidence in COVERAGE-103.json.',
              browser_validation='Code-level DOM stand-in only; browser local-file URL policy rejected visual inspection. No circumvention attempted.',
              goal_state='Incomplete: source074 remains a partial pack, runtime/all-map visual coverage incomplete, manual review queue retained. Latest user pivot excludes new automatic matching/upscales/filtering.')
(root / 'outputs/TEXTURES-103-state.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k in ['counts','merged_original_ids','merged_image_files','native_binary_sha256','artifact_sha256','goal_state']},indent=2))
