"""Record final source snapshot and artifact hashes without circular hashing."""
import hashlib, json, zipfile
from pathlib import Path
root = Path(__file__).resolve().parent.parent
sha = lambda path: hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
manifest = json.loads((root/'outputs/SOURCE-100-manifest.json').read_text())
archive = root/'outputs/SOURCE-100.zip'
assert sha(archive) == manifest['archive_sha256']
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name,digest in manifest['source_sha256'].items():
        assert hashlib.sha256(z.read(name)).hexdigest() == digest, name
        assert sha(root/name) == digest, name
names = ['outputs/CHECKPOINT-100.md','outputs/RENDERING-100.md',
         'outputs/SOURCE-100-manifest.json','outputs/TEXTURES-100-state.json',
         'outputs/COVERAGE-100.json','outputs/TEXTURE-MUTABILITY-100.json',
         'work/build-windows-native/bin/RenegadeNative.exe']
receipt = dict(snapshot='outputs/SOURCE-100.zip', archive_sha256=sha(archive),
               source_files=manifest['file_count'], verified_every_entry=True,
               git_head=manifest['git_head'], artifact_sha256={name:sha(root/name) for name in names},
               goal='active/incomplete', scope='Source-only snapshot; external proprietary assets/dependencies/binaries remain separately retained.')
path = root/'outputs/SOURCE-100-receipt.json'
assert not path.exists(), 'Receipt already exists; use a new checkpoint number.'
path.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
