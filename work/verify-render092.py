"""Verify terminal final GPU/software runs and retain actual 720p captures."""
import hashlib,json,re,struct,io
from pathlib import Path
from PIL import Image
import numpy as np
r=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
reports={};outputs={}
for renderer in ['gpu','software']:
 run=r/f'work/runs/render092-final-{renderer}'
 state=json.loads((run/'run.json').read_text());assert state['state']=='finished' and state['exit_code']==0 and not state['timed_out']
 log=(run/'native.log').read_text()
 expected='active=directx12 target=1280x720 msaa=4' if renderer=='gpu' else 'active=software'
 assert expected in log
 summary=re.search(r'\[ge-backend-result\] (.*)',log).group(1)
 reports[renderer]={'run':state,'native_log_sha256':sha(run/'native.log'),'gpu_summary':summary,
  'config_sha256':sha(Path(state['environment']['PSPRECOMP_CONFIG']))}
 files={'unfiltered':run/'gpu.ppm','fxaa':run/'gpu-fxaa.ppm'} if renderer=='gpu' else {
  'unfiltered':run/'frames/render-720p/frame_002479.ppm','fxaa':run/'frames/render-720p-fxaa/frame_002479.ppm'}
 arrays={}
 for mode,p in files.items():
  image=Image.open(p).convert('RGB');assert image.size==(1280,720)
  dst=r/f'outputs/render092-final-{renderer}-{mode}.png';image.save(dst)
  outputs[f'{renderer}_{mode}']={'file':str(dst.relative_to(r)),'png_sha256':sha(dst),'ppm_sha256':sha(p)}
  arrays[mode]=np.asarray(image)
 assert np.any(arrays['unfiltered']!=arrays['fxaa']),f'{renderer} FXAA must be applied'
 reports[renderer]['fxaa_changed_pixels']=int(np.any(arrays['unfiltered']!=arrays['fxaa'],axis=2).sum())
 if renderer=='gpu':
  fields=dict(item.split('=',1) for item in summary.split())
  assert int(fields['replacement_uploads'])>0 and fields['missing_textures']=='0'
 else:
  report=run/'render-report.jsonl';records=[json.loads(s) for s in report.read_text().splitlines()]
  reports[renderer]['last_probe_frame']=next(s for s in records if s['vblank']==2479)
native_hash=sha(r/'work/build-windows-native/bin/RenegadeNative.exe')
assert all(report['run']['native_binary_sha256']==native_hash for report in reports.values())
dumps=r/'work/texture-dumps-live/textures';ids=set()
for p in dumps.glob('*.tga'):
 data=p.read_bytes();im=Image.open(io.BytesIO(data+b'\0'*max(0,26-len(data)))).convert('RGBA')
 digest=hashlib.sha256(struct.pack('<II',*im.size)+im.tobytes()).hexdigest();assert p.stem=='tex-v1-'+digest
 ids.add(p.stem)
archive_ids={p.stem for p in dumps.glob('*.png')}
pack=r/'work/mods-textures-source074'
report={'native_binary_sha256':native_hash,'runs':reports,'images':outputs,
 'tests':{'override':'7/7','physical_dx12':'1/1','display':'1/1'},
 'pack_file_sha256':{str(p.relative_to(r)):sha(p) for p in sorted(pack.rglob('*')) if p.is_file()},
 'archive_png_ids':len(archive_ids),'verified_runtime_tga_ids':len(ids),'unique_dump_ids':len(archive_ids|ids),
 'policy':'No new mipmaps/filtering, image rotation, channel swap or new source matching. GPU replacement uploads use one full-size authored level.',
 'limits':['Texture-only GPU preview; model/material packs reject.','Readback plus CPU reference raster remains enabled.','Runs executed concurrently; elapsed times are not a fair performance comparison.','No all-map visual/gameplay acceptance.']}
(r/'outputs/RENDER-092-state.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'binary':native_hash,'runs':{k:{'exit':v['run']['exit_code'],'elapsed':v['run']['elapsed_seconds'],'summary':v['gpu_summary'],'fxaa_changed_pixels':v['fxaa_changed_pixels']} for k,v in reports.items()},'dump_ids':report['unique_dump_ids']},indent=2))
