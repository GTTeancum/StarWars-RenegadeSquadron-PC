"""Record rendering integration evidence and verify original runtime texture IDs."""
import hashlib,json,struct,io
from pathlib import Path
from PIL import Image
r=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
run=r/'work/runs/render090-echo'
result=json.loads((run/'run.json').read_text())
assert result['exit_code']==0 and not result['timed_out']
assert '[display-sdl] internal=1280x720 fxaa=1 guest_vram_preserved=1' in (run/'native.log').read_text()
capture=run/'frames/render-720p-fxaa/frame_002479.ppm'
im=Image.open(capture);assert im.size==(1280,720)
out=r/'outputs/render090-echo-720p-fxaa.png';im.save(out)
dumps=r/'work/texture-dumps-live/textures'
runtime=list(dumps.glob('*.tga'))
ids=set()
for p in runtime:
 data=p.read_bytes()
 # Pillow seeks 26 bytes backward for an optional footer, even on a valid 22-byte 1x1 TGA.
 image=Image.open(io.BytesIO(data+b'\0'*max(0,26-len(data)))).convert('RGBA')
 digest=hashlib.sha256(struct.pack('<II',*image.size)+image.tobytes()).hexdigest()
 assert p.stem=='tex-v1-'+digest,p.name
 ids.add(p.stem)
png_ids={p.stem for p in dumps.glob('*.png')}
report={'run':result,'integration_binary_note':'Final rebuild changes startup log wording only; run binary identity retained separately.',
 'current_binary_sha256':sha(r/'work/build-windows-native/bin/RenegadeNative.exe'),
 'presentation_verified':'SDL dummy driver executed normal presentation path at 1280x720 with FXAA. HD enabled at vblank 2465; this does not establish whole-session HD performance.',
 'screenshot':str(out.relative_to(r)),'screenshot_sha256':sha(out),'native_log_sha256':sha(run/'native.log'),
 'archive_original_pngs':len(png_ids),'runtime_original_tgas_verified':len(ids),'unique_original_ids':len(png_ids|ids),
 'dump_manifest_sha256':sha(dumps/'textures.jsonl'),
 'tests':{'override_ctest':'7/7 passed after renderer/frame-boundary changes','display_ctest':'1/1 passed; final startup-log rebuild rechecked separately'},
 'limitations':['Software double rasterization performance unmeasured in full play.','Startup/video/direct CPU framebuffer can use guest fallback.','Catalog and encountered dumps do not prove every dynamic texture or every map state.','No automatic source matching or upscaling in this pivot.']}
(r/'outputs/RENDER-090-state.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['current_binary_sha256','archive_original_pngs','runtime_original_tgas_verified','unique_original_ids','screenshot_sha256']},indent=2))
