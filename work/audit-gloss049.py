"""Audit real gloss vertex-light diagnostics, not pixel-level highlight visibility."""
import hashlib,json,re
from pathlib import Path
root=Path(__file__).resolve().parent.parent;run=root/'work/runs/gloss049-adapted'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
meta=json.loads((run/'run.json').read_text())
assert meta['state']=='finished' and meta['exit_code']==0 and not meta['timed_out']
assert any('VBlank diagnostic stop at 2576' in s for s in meta['stop_lines'])
log=(run/'native.log').read_text(errors='replace')
fields=['submitted','prepared','pixels_written','gloss_vertices','highlight_vertices','max_highlight','gloss_lights','max_light_specular','diffuse_gloss_lights']
def values(line):return {k:float(re.search(r'\b'+k+r'=([0-9.eE+-]+)',line)[1]) for k in fields}
draws=[values(s) for s in log.splitlines() if '[overrides] Skinned MSH draw ' in s]
assert len(draws)==8 and all(d['submitted']==1378 and d['pixels_written']>0 and d['gloss_vertices']>0 for d in draws)
assert 'Skin deformation failed' not in log
assert any(d['highlight_vertices']>0 and d['max_highlight']>0 and d['diffuse_gloss_lights']>0 for d in draws)
synthetic=(root/'outputs/GLOSS-049-synthetic.log').read_text(errors='replace')
assert '94 model integration checks passed' in synthetic
white=values(next(s for s in synthetic.splitlines() if 'MSH draw ' in s and '\\gloss-white\\' in s))
unlit=values(next(s for s in synthetic.splitlines() if 'MSH draw ' in s and '\\gloss-unlit\\' in s))
assert white['highlight_vertices']==6 and white['max_highlight']==255
assert unlit['highlight_vertices']==0 and unlit['max_highlight']==0
paths=[Path(__file__),run/'run.json',run/'native.log',run/'frames/frame_002575.ppm',root/'outputs/GLOSS-049-tests.log',root/'outputs/GLOSS-049-synthetic.log',root/'work/build-windows-native/bin/RenegadeNative.exe',root/'work/project/source/profiles/vcs/host/ge_renderer.cpp',root/'work/project/source/profiles/renegade/tests/override_model.cpp']
report={'scope':'Eight early real draws; highlights measured before clipping, texture-alpha masking and visibility','native_run':meta,'draws':draws,'synthetic_checks':94,'sha256':{p.relative_to(root).as_posix():sha(p) for p in paths}}
(root/'outputs/GLOSS-049-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['sha256','native_run']},indent=2))
