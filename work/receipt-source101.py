"""Verify final source state and record final artifacts independently."""
import hashlib,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
m=json.loads((root/'outputs/SOURCE-101-manifest.json').read_text())
archive=root/'outputs/SOURCE-101.zip'
assert sha(archive)==m['archive_sha256']
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name,digest in m['source_sha256'].items():
        assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
        assert sha(root/name)==digest,name
names=['outputs/CHECKPOINT-101.md','outputs/RENDERING-101.md',
       'outputs/CHECKPOINT-101-progress.md','outputs/SOURCE-101-manifest.json',
       'outputs/CHECKPOINT-101-progress2.md',
       'outputs/TEXTURES-101-state.json','outputs/COVERAGE-101.json',
       'outputs/TEXTURE-MUTABILITY-101.json','work/build-windows-native/bin/RenegadeNative.exe']
receipt=dict(snapshot='outputs/SOURCE-101.zip',archive_sha256=sha(archive),
             source_files=m['file_count'],verified_every_entry=True,git_head=m['git_head'],
             artifact_sha256={n:sha(root/n) for n in names},goal='active/incomplete',
             scope='Source-only snapshot; native unchanged from tested 100; proprietary assets/dependencies/binaries separately retained.')
p=root/'outputs/SOURCE-101-receipt.json';assert not p.exists();p.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
