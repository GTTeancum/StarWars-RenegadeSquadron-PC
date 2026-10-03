"""Verify consolidated original pixels, links and unchanged tested renderer state."""
import hashlib, io, json, struct
from pathlib import Path
from PIL import Image
root = Path(__file__).resolve().parent.parent
sha = lambda p: hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
catalog = json.loads((root / 'work/texture-catalog098/catalog.json').read_text())
ids = {r['id'] for r in catalog['images']}
assert len(ids) == len(catalog['images']) == catalog['counts']['catalog_unique_ids']
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
manifest = json.loads((root / 'outputs/SOURCE-097-manifest.json').read_text())
cpp = ['work/project/source/profiles/vcs/host/ge_renderer.cpp',
       'work/project/source/profiles/vcs/host/ge_gpu_backend_dx12.cpp',
       'work/project/source/profiles/vcs/host/ge_gpu_backend.hpp',
       'work/project/source/profiles/renegade/host/display_sdl.cpp',
       'work/project/source/profiles/renegade/host/main.cpp',
       'work/project/source/profiles/renegade/host/psp_services.cpp']
native_sources = {name:digest for name,digest in manifest['source_sha256'].items()
                  if name.startswith('work/project/source/')}
for name in native_sources:
    assert sha(root / name) == manifest['source_sha256'][name], name
for name,digest in catalog['render_target_evidence_sha256'].items():
    assert sha(root/name) == digest, name
assert sum(row['render_target_sample'] for row in catalog['images']) == 798
for row in catalog['images']:
    assert row['render_target_sample'] == bool(row['render_target_records']), row['id']
    for record in row['render_target_records']:
        assert record['run'] and (record['address'] & 0x3f000000) == 0x04000000
        assert record['format'] == 3 and not record['swizzled']
        assert record['width'] == record['height'] == record['buffer_width'] == 512
binary = sha(root / 'work/build-windows-native/bin/RenegadeNative.exe')
assert binary == '572c9e0754a939acbc9e4a76da92ad50e76b11245a173fe53fc99f680d38e164'
sources = json.loads((root / 'outputs/TEXTURE-SOURCES-095.json').read_text())
assert not sources['failures'] and sources['image_count'] == 13820 and len(sources['archives']) == 12
assert not any(catalog[k] for k in ['unsupported','uncatalogued_texture_archives','runtime_errors','pack_errors'])
artifacts = ['work/texture-catalog098/catalog.json', 'work/texture-catalog098/index.html',
             'work/texture-catalog098/textures.csv', 'work/texture-catalog098/runtime-review.csv',
             'work/texture-catalog098/original-sources.csv', 'work/texture-catalog098/original-sources.json', 'outputs/COVERAGE-098.json', 'outputs/TEXTURE-MUTABILITY-098.json', 'work/texture-catalog098/mutable-sources.csv', 'outputs/FOG-097-final-build-tests.txt', 'outputs/FOG-097-before-tests.txt', 'outputs/FOG-097-test-detail.txt',
             'outputs/TEXTURE-CATALOG-098.json', 'outputs/TEXTURE-COVERAGE-098.md',
             'outputs/TEXTURE-SOURCES-095.json', 'outputs/TEXTURE-098-browser-tests.txt']
report = dict(counts=catalog['counts'], merged_original_ids=len(found), merged_image_files=len(files),
              original_file_sha256=files, artifact_sha256={name:sha(root/name) for name in artifacts},
              unchanged_renderer_sha256={name:sha(root/name) for name in cpp}, unchanged_native_source_files=len(native_sources), native_binary_sha256=binary,
              sources=sources, renderer_validation='Inherited final checkpoint 097 rendering suite; native source/executable unchanged in 098. New map/era/mode runtime evidence in COVERAGE-098.json. No unneeded rebuild/repetition of native tests.',
              browser_validation='Code-level DOM stand-in only; browser local-file URL policy rejected visual inspection. No circumvention attempted.',
              goal_state='Incomplete: source074 remains a partial pack, runtime/all-map visual coverage incomplete, manual review queue retained. Latest user pivot excludes new automatic matching/upscales/filtering.')
(root / 'outputs/TEXTURES-098-state.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k in ['counts','merged_original_ids','merged_image_files','native_binary_sha256','artifact_sha256','goal_state']},indent=2))
