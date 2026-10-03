"""Fetch official portable Real-ESRGAN/RealESRNet and record immutable identities."""
import hashlib,json,urllib.request,zipfile
from pathlib import Path
root=Path(__file__).resolve().parent.parent
url='https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip'
archive=root/'work/upscale-tools/realesrgan-ncnn-vulkan-20220424-windows.zip'
dest=root/'work/upscale-tools/official-20220424'
archive.parent.mkdir(exist_ok=True)
if not archive.exists():
 partial=archive.with_suffix('.download')
 with urllib.request.urlopen(url,timeout=60) as response,partial.open('wb') as output:
  while chunk:=response.read(1024*1024):output.write(chunk)
 partial.replace(archive)
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for info in z.infolist():
  target=(dest/info.filename).resolve();assert target.is_relative_to(dest.resolve())
  if info.is_dir():target.mkdir(parents=True,exist_ok=True);continue
  data=z.read(info);target.parent.mkdir(parents=True,exist_ok=True)
  if target.exists():assert target.read_bytes()==data
  else:target.write_bytes(data)
files={p.relative_to(root).as_posix():sha(p) for p in dest.rglob('*') if p.is_file()}
report=dict(source_url=url,archive_sha256=sha(archive),archive_size=archive.stat().st_size,zip_integrity=True,file_sha256=files,
 selected_model='realesrnet-x4plus',model_source='https://github.com/xinntao/Real-ESRGAN/blob/master/docs/model_zoo.md',
 selection='Official model zoo describes this as X4 trained with MSE loss, with potential over-smoothing. Validate actual textures before accepting the pack. No GAN/face/anime enhancement.')
out=root/'outputs/UPSCALER-106-intake.json'
if out.exists():assert json.loads(out.read_text())==report
else:out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
