"""Recover the official MSE model absent from the20220424 portable bundle."""
import hashlib,json,urllib.request,zipfile
from pathlib import Path
root=Path(__file__).resolve().parent.parent
url='https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.2/realesrgan-ncnn-vulkan-20210801-windows.zip'
archive=root/'work/upscale-tools/realesrgan-ncnn-vulkan-20210801-windows.zip'
dest=root/'work/upscale-tools/official-20210801'
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
models=[p for p in dest.rglob('*') if p.is_file() and 'esrnet' in p.name.lower()]
assert models,'Official older bundle also lacks the selected model'
report=dict(source_url=url,archive_sha256=sha(archive),zip_integrity=True,
 file_sha256={p.relative_to(root).as_posix():sha(p) for p in dest.rglob('*') if p.is_file()},
 model_paths=[p.relative_to(root).as_posix() for p in models],
 reason='20220424 Windows bundle inspection proves realesrnet-x4plus.bin/param absent. Older official release supplies MSE model; no third-party model substitution.')
p=root/'outputs/UPSCALER-106-psnr-model-intake.json'
if p.exists():assert json.loads(p.read_text())==report
else:p.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
