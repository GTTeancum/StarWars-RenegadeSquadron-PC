"""Validate completed 720p/FXAA gameplay runs and export lossless review PNGs."""
import hashlib,json,re
from pathlib import Path
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parent.parent
pack=json.loads((root/'outputs/TEXTURE-PACK-061.json').read_text())
bindings={f['id']:f for f in pack['files']}
report={'runs':{},'comparisons':{},'note':'Static scenery comparison; replay does not synchronize NPC animations.'}
for version in ('baseline','updated'):
    folder=root/f'work/runs/source061-fxaa-{version}'
    run=json.loads((folder/'run.json').read_text())
    assert run['state']=='finished' and run['exit_code']==0 and not run['timed_out']
    assert run['environment']['PSPRECOMP_WINDOW']=='0'
    log=(folder/'native.log').read_text()
    assert log.count('shadow_raster=1280x720')==2 and log.count('fxaa=1 output=1280x720')==2
    loaded=sorted(set(re.findall(r'\[overrides\] texture (tex-v1-[a-f0-9]+) loaded',log)))
    report['runs'][version]={'run':run,'loaded':[bindings[i] for i in loaded],'frames':[]}
    for frame in (2519,2639):
        images={}
        for kind in ('render-720p','render-720p-fxaa'):
            path=folder/f'frames/{kind}/frame_{frame:06d}.ppm'
            image=Image.open(path).convert('RGB');assert image.size==(1280,720)
            dest=root/f'outputs/SOURCE-061-{version}-{kind}-{frame}.png'
            image.save(dest);images[kind]=np.array(image)
        raw=images['render-720p'];filtered=images['render-720p-fxaa']
        changed=np.any(raw!=filtered,axis=2)
        assert changed.any() and not changed.all()
        report['runs'][version]['frames'].append({'vblank':frame,'fxaa_changed_pixels':int(changed.sum()),
                                                 'pixels':1280*720,'raw_and_filtered_dimensions':[1280,720]})
for frame in (2519,2639):
    before=np.array(Image.open(root/f'outputs/SOURCE-061-baseline-render-720p-fxaa-{frame}.png'))
    after=np.array(Image.open(root/f'outputs/SOURCE-061-updated-render-720p-fxaa-{frame}.png'))
    # Static bunker panel away from player, reticle, moving NPCs and UI.
    a=before[240:380,55:405].astype(int);b=after[240:380,55:405].astype(int)
    report['comparisons'][str(frame)]={'static_wall_roi_xyxy':[55,240,405,380],
        'changed_pixels':int(np.any(a!=b,axis=2).sum()),'roi_pixels':49000,
        'mean_absolute_rgb_difference':float(np.abs(a-b).mean())}
(root/'outputs/SOURCE-061-final-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
paths=[root/'Play-RenegadeSquadronPC.ps1',root/'Capture-Texture-Baseline.ps1',
       root/'work/build-windows-native/bin/RenegadeNative.exe',root/'work/source060-echo-replay.txt',
       root/'work/project/source/profiles/vcs/host/ge_renderer.cpp',
       root/'work/project/source/profiles/vcs/host/ge_renderer.hpp',
       root/'work/project/source/profiles/vcs/host/framebuffer_capture.cpp',
       root/'work/project/source/profiles/renegade/tests/override_render.cpp']
paths+=list((root/'outputs').glob('*061*.json'))+list((root/'outputs').glob('*061*.png'))
paths+=list((root/'outputs').glob('TESTS-061*.txt'))
paths+=list((root/'work/mods-textures-source061/textures').iterdir())
state={'sha256':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
       'scope':'Verified local build, pack, reports and captures; no all-map coverage claim.'}
(root/'outputs/TEXTURES-061-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps({'loaded':{k:len(v['loaded']) for k,v in report['runs'].items()},
                  'comparisons':report['comparisons'],'hashed_files':len(state['sha256'])},indent=2))
