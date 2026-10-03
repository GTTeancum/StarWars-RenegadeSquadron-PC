"""Verify the completed source snapshot and final milestone artifacts."""
import hashlib,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
m=json.loads((root/'outputs/SOURCE-106-manifest.json').read_text());archive=root/'outputs/SOURCE-106.zip'
assert sha(archive)==m['archive_sha256']
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for name,digest in m['source_sha256'].items():
  assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
  assert sha(root/name)==digest,name
names=['outputs/CHECKPOINT-106.md','outputs/RENDERING-106.md','outputs/TEXTURE-PACK-106-ui2.json','outputs/UPSCALER-106-plan.json',
 'outputs/UPSCALER-106-ui2-verification.json','outputs/UPSCALER-106-gameplay.json','outputs/UPSCALER-106-visual-samples.json',
 'outputs/TEXTURES-106-state.json','outputs/TEXTURE-MUTABILITY-106.json','outputs/TEXTURE-106-browser-tests.txt',
 'outputs/UPSCALER-106-ui2-launcher-dryrun.txt','outputs/UPSCALER-106-comparison-verification.json','outputs/SOURCE-106-manifest.json','work/upscale106/batch/run.json',
 'work/texture-catalog106/catalog.json','work/texture-catalog106/index.html','work/build-windows-native/bin/RenegadeNative.exe']
r=dict(snapshot='outputs/SOURCE-106.zip',archive_sha256=sha(archive),source_files=m['file_count'],verified_every_entry=True,
 git_head=m['git_head'],artifact_sha256={n:sha(root/n) for n in names},
 scope='Source-only final milestone snapshot. Original/game/upscaled image payloads and native/upscaler/model/dependency binaries separately retained locally and hashed in provenance. Not a fresh-machine restoration test. Larger game/full-mission work remains open.')
p=root/'outputs/SOURCE-106-receipt.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
