"""Verify checkpoint107 source snapshot and final artifacts."""
import hashlib,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parent.parent;sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest();m=json.loads((root/'outputs/SOURCE-107-manifest.json').read_text());archive=root/'outputs/SOURCE-107.zip';assert sha(archive)==m['archive_sha256']
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for name,digest in m['source_sha256'].items():assert hashlib.sha256(z.read(name)).hexdigest()==digest and sha(root/name)==digest
names=['outputs/CHECKPOINT-107.md','outputs/RENDERING-107.md','outputs/TEXTURE-PACK-107.json','outputs/UPSCALER-107-plan.json','outputs/UPSCALER-107-verification.json','outputs/UPSCALER-107-gameplay.json','outputs/UPSCALER-107-raw-review.json','outputs/UPSCALER-107-comparison-verification.json','outputs/TEXTURES-107-state.json','outputs/TEXTURE-MUTABILITY-107.json','outputs/TEXTURE-107-browser-tests.txt','outputs/RENDERING-107-build-tests.txt','outputs/UPSCALER-107-launcher-dryrun.txt','outputs/SOURCE-107-manifest.json','work/upscale107/batch/run.json','work/texture-catalog107/catalog.json','work/texture-catalog107/index.html','work/build-windows-native/bin/RenegadeNative.exe']
r=dict(snapshot='outputs/SOURCE-107.zip',archive_sha256=sha(archive),source_files=m['file_count'],verified_every_entry=True,git_head=m['git_head'],artifact_sha256={n:sha(root/n) for n in names},scope='Source-only checkpoint107 snapshot. Game/original/generated texture payloads and upscaler/model/dependency/native binaries remain separate locally with recorded hashes. Not a fresh-machine restoration test.')
p=root/'outputs/SOURCE-107-receipt.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
