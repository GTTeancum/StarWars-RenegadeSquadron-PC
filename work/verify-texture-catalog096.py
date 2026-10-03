"""Verify consolidated original pixels, links and unchanged tested renderer state."""
import hashlib, io, json, struct
from pathlib import Path
from PIL import Image
root = Path(__file__).resolve().parent.parent
sha = lambda p: hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
catalog = json.loads((root / 'work/texture-catalog096/catalog.json').read_text())
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
manifest = json.loads((root / 'outputs/SOURCE-094-manifest.json').read_text())
cpp = ['work/project/source/profiles/vcs/host/ge_renderer.cpp',
       'work/project/source/profiles/vcs/host/ge_gpu_backend_dx12.cpp',
       'work/project/source/profiles/vcs/host/ge_gpu_backend.hpp',
       'work/project/source/profiles/renegade/host/display_sdl.cpp',
       'work/project/source/profiles/renegade/host/main.cpp',
       'work/project/source/profiles/renegade/host/psp_services.cpp']
for name in cpp:
    assert sha(root / name) == manifest['source_sha256'][name], name
binary = sha(root / 'work/build-windows-native/bin/RenegadeNative.exe')
assert binary == '076acd42f4240f268f286f8dd9b16c85cd80a6ad830e68412bfa02940a38f223'
sources = json.loads((root / 'outputs/TEXTURE-SOURCES-095.json').read_text())
assert not sources['failures'] and sources['image_count'] == 13820 and len(sources['archives']) == 12
assert not any(catalog[k] for k in ['unsupported','uncatalogued_texture_archives','runtime_errors','pack_errors'])
artifacts = ['work/texture-catalog096/catalog.json', 'work/texture-catalog096/index.html',
             'work/texture-catalog096/textures.csv', 'work/texture-catalog096/runtime-review.csv',
             'work/texture-catalog096/original-sources.csv', 'work/texture-catalog096/original-sources.json', 'outputs/COVERAGE-096.json',
             'outputs/TEXTURE-CATALOG-096.json', 'outputs/TEXTURE-COVERAGE-096.md',
             'outputs/TEXTURE-SOURCES-095.json', 'outputs/TEXTURE-096-browser-tests.txt']
report = dict(counts=catalog['counts'], merged_original_ids=len(found), merged_image_files=len(files),
              original_file_sha256=files, artifact_sha256={name:sha(root/name) for name in artifacts},
              unchanged_renderer_sha256={name:sha(root/name) for name in cpp}, native_binary_sha256=binary,
              sources=sources, renderer_validation='Inherited checkpoint 094 results; renderer and executable unchanged in 096.',
              browser_validation='Code-level DOM stand-in only; browser local-file URL policy rejected visual inspection. No circumvention attempted.',
              goal_state='Incomplete: source074 remains a partial pack, runtime/all-map visual coverage incomplete, manual review queue retained. Latest user pivot excludes new automatic matching/upscales/filtering.')
(root / 'outputs/TEXTURES-096-state.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k in ['counts','merged_original_ids','merged_image_files','native_binary_sha256','artifact_sha256','goal_state']},indent=2))
