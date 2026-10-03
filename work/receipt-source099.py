"""Record final source snapshot and artifact hashes without circular hashing."""
import hashlib, json, zipfile
from pathlib import Path
root = Path(__file__).resolve().parent.parent
sha = lambda path: hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
manifest = json.loads((root/'outputs/SOURCE-099-manifest.json').read_text())
archive = root/'outputs/SOURCE-099.zip'
assert sha(archive) == manifest['archive_sha256']
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name,digest in manifest['source_sha256'].items():
        assert hashlib.sha256(z.read(name)).hexdigest() == digest, name
        assert sha(root/name) == digest, name
names = ['outputs/CHECKPOINT-099.md','outputs/RENDERING-099.md',
         'outputs/SOURCE-099-manifest.json','outputs/TEXTURES-099-state.json',
         'outputs/COVERAGE-099.json','outputs/TEXTURE-MUTABILITY-099.json',
         'work/build-windows-native/bin/RenegadeNative.exe']
receipt = dict(snapshot='outputs/SOURCE-099.zip', archive_sha256=sha(archive),
               source_files=manifest['file_count'], verified_every_entry=True,
               git_head=manifest['git_head'], artifact_sha256={name:sha(root/name) for name in names},
               goal='active/incomplete', scope='Source-only snapshot; external proprietary assets/dependencies/binaries remain separately retained.')
path = root/'outputs/SOURCE-099-receipt.json'
assert not path.exists(), 'Receipt already exists; use a new checkpoint number.'
path.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
