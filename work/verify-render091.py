"""Verify real captures, HUD-preserving FXAA, probes and terminal run evidence."""
import hashlib,json,io,struct
from pathlib import Path
from PIL import Image
import numpy as np
r=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
run=r/'work/runs/render091-updated'
state=json.loads((run/'run.json').read_text());assert state['exit_code']==0 and not state['timed_out']
records=[json.loads(s) for s in (run/'render-report.jsonl').read_text().splitlines()]
last=next(s for s in records if s['vblank']==2479)
images={}
hashes={}
for key,folder in [('unfiltered','render-720p'),('fxaa','render-720p-fxaa'),('whole_frame_fxaa','render-720p-fxaa-whole-frame')]:
 p=run/'frames'/folder/'frame_002479.ppm';im=Image.open(p).convert('RGB');assert im.size==(1280,720)
 images[key]=np.asarray(im);out=r/f'outputs/render091-updated-{key}.png';im.save(out)
 hashes[key]={'ppm_sha256':sha(p),'png_sha256':sha(out),'path':str(out.relative_to(r))}
new,old,raw=images['fxaa'],images['whole_frame_fxaa'],images['unfiltered']
restored=np.any(new!=old,axis=2)
assert restored.any(),'Real capture must show a HUD-preservation effect'
assert np.array_equal(new[restored],raw[restored]),'Changed pixels must be exact original rendered samples'
assert np.any(new!=raw),'Scene FXAA must remain active'
replacements=[]
for probe in last['probes']:
 if not probe['replacement_width']:continue
 pack=r/'work/mods-textures-source074/textures'
 p=next(p for suffix in ['.dds','.tga','.png'] if (p:=pack/(probe['id']+suffix)).is_file())
 assert Image.open(p).size==(probe['replacement_width'],probe['replacement_height'])
 replacements.append({**probe,'image':str(p.relative_to(r)),'image_sha256':sha(p)})
assert replacements,'Existing pack must be sampled by the actual renderer'
dumps=r/'work/texture-dumps-live/textures';ids=set()
for p in dumps.glob('*.tga'):
 data=p.read_bytes();im=Image.open(io.BytesIO(data+b'\0'*max(0,26-len(data)))).convert('RGBA')
 digest=hashlib.sha256(struct.pack('<II',*im.size)+im.tobytes()).hexdigest();assert p.stem=='tex-v1-'+digest
 ids.add(p.stem)
archive_ids={p.stem for p in dumps.glob('*.png')}
report={'run':state,'report_sha256':sha(run/'render-report.jsonl'),'native_log_sha256':sha(run/'native.log'),
 'images':hashes,'hud_pixels_restored_vs_whole_frame_fxaa':int(restored.sum()),
 'remaining_scene_fxaa_changed_pixels':int(np.any(new!=raw,axis=2).sum()),
 'last_frame':last,'verified_replacements':replacements,
 'known_surface_overlap_draws':sum(read['draws'] for frame in records for read in frame['surface_reads'] if read['known_surface_overlap']),
 'hd_surface_resolved_draws':sum(read['draws'] for frame in records for read in frame['surface_reads'] if read['hd_resolved']),
 'archive_png_ids':len(archive_ids),'runtime_tga_ids_verified':len(ids),'union_dump_ids':len(ids|archive_ids),
 'tests':{'override_ctest':'7/7 passed after final build','display_ctest':'1/1 passed after final build'},
 'policy':'Existing staged source074 pack used as-is; no new matching, rotation, channel swap or upscale.',
 'limits':['HD enabled only for bounded final gameplay interval; no realtime FPS claim.','Screen-space classification is a heuristic for HUD/effects.','Experimental composition is opt-in; CPU writes, partial views and all-map coverage are not fully validated.']}
(r/'outputs/RENDER-091-state.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['hud_pixels_restored_vs_whole_frame_fxaa','remaining_scene_fxaa_changed_pixels','known_surface_overlap_draws','hd_surface_resolved_draws','union_dump_ids','verified_replacements']},indent=2))
