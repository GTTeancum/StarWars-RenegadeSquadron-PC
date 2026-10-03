"""Verify final source state and record final artifacts independently."""
import hashlib,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
m=json.loads((root/'outputs/SOURCE-102-manifest.json').read_text())
archive=root/'outputs/SOURCE-102.zip'
assert sha(archive)==m['archive_sha256']
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name,digest in m['source_sha256'].items():
        assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
        assert sha(root/name)==digest,name
names=['outputs/CHECKPOINT-102.md','outputs/RENDERING-102.md',
       'outputs/CHECKPOINT-102-progress.md','outputs/SOURCE-102-manifest.json',
       'outputs/CHECKPOINT-102-progress2.md',
       'outputs/TEXTURES-102-state.json','outputs/COVERAGE-102.json',
       'outputs/TEXTURE-MUTABILITY-102.json','work/build-windows-native/bin/RenegadeNative.exe']
receipt=dict(snapshot='outputs/SOURCE-102.zip',archive_sha256=sha(archive),
             source_files=m['file_count'],verified_every_entry=True,git_head=m['git_head'],
             artifact_sha256={n:sha(root/n) for n in names},goal='active/incomplete',
             scope='Source-only snapshot; native unchanged from tested 100 and verified 101; proprietary assets/dependencies/binaries separately retained.')
p=root/'outputs/SOURCE-102-receipt.json';assert not p.exists();p.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
