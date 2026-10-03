"""Revalidate 101 source archive and actual state before new coverage work."""
import hashlib,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
receipt=json.loads((root/'outputs/SOURCE-103-receipt.json').read_text())
manifest=json.loads((root/'outputs/SOURCE-103-manifest.json').read_text())
for name,digest in receipt['artifact_sha256'].items():assert sha(root/name)==digest,name
archive=root/receipt['snapshot'];assert sha(archive)==receipt['archive_sha256']
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name,digest in manifest['source_sha256'].items():
        assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
        assert sha(root/name)==digest,name
report=dict(prior_turn='progress: eight completed menu/GC checks, a bounded campaign timeout, 37 environment opens, three new original IDs and verified source snapshot',
            verified_source_files=manifest['file_count'],verified_artifact_files=len(receipt['artifact_sha256']),
            source_archive_sha256=sha(archive),native_binary_sha256=sha(root/'work/build-windows-native/bin/RenegadeNative.exe'),
            native_sources_unchanged=sum(n.startswith('work/project/source/') for n in manifest['source_sha256']),
            scope='All recorded 103 source/archive entries and receipt artifacts matched current files; new 104 tools excluded from prior inventory.')
(root/'outputs/PRIOR-104-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
