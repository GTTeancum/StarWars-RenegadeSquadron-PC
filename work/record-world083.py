"""Preserve exact native run, material fallback, source and test evidence."""
import hashlib,json,re
from pathlib import Path
r=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
names=['coverage083-korriban','converted083-korriban','converted083b-korriban','converted083c-korriban','converted083-ordmantell']
runtime={};files=[]
for name in names:
    run=r/'work/runs'/name;state=json.loads((run/'run.json').read_text())
    assert state['state']=='finished' and state['exit_code']==0 and not state['timed_out']
    entry=dict(state=state)
    if name.startswith('converted'):
        log=(run/'native.log').read_text()
        expected=13 if 'ordmantell' in name else 50
        assert f'Converted world geometry loaded models={expected}' in log
        samples=[json.loads(line) for line in (run/'world-report.jsonl').read_text().splitlines()]
        assert samples and any(s['matched_draws']>0 and s['matched_triangles']>0 for s in samples)
        target=2574 if 'ordmantell' in name else 2510
        entry.update(models_loaded=expected,frame_report=next(s for s in samples if s['vblank']==target),report_scope='Candidate attempts include dynamic objects/effects; counts do not establish a static-map completeness percentage.')
        files.append(run/'world-report.jsonl')
    runtime[name]=entry;files += [run/'run.json',run/'native.log']
assert runtime['converted083c-korriban']['state']['native_binary_sha256']==sha(r/'work/build-windows-native/bin/RenegadeNative.exe')
tests=(r/'outputs/WORLD-083-tests.log').read_text();assert tests.count('Test Passed.')==7
checks=int(re.search(r'(\d+) model integration checks passed',tests).group(1));assert checks==146
staged={}
for world in ['KOR','PSO']:
    path=r/f'outputs/WORLD-STAGE-083-{world}.json';stage=json.loads(path.read_text())
    for name,digest in stage['asset_sha256'].items():assert sha(r/name)==digest
    staged[world]=stage;files.append(path)
files += [r/'work/build-windows-native/bin/RenegadeNative.exe',r/'outputs/WORLD-083-tests.log',r/'outputs/WORLD-083-archive-test.log',r/'Capture-Converted-Map.ps1',r/'Play-RenegadeSquadronPC.ps1']
files += list((r/'outputs').glob('*083*.png'))
files += [r/'work/project/source/profiles/renegade/host'/name for name in ['override_model.hpp','override_model.cpp','override_world.hpp','override_world.cpp','override_skin.cpp']]
files.append(r/'work/project/source/profiles/vcs/host/ge_renderer.cpp')
archive=r/'SWBF2 PSP mod maps/data_KOR FINAL.7z'
assert sha(archive)=='6f2ed060e10a53d1238c98de842d83207d2ebd6cc4c036044139320b3d1a21c3'
report=dict(scope='Two converted-map spawn views at actual 720p/FXAA. Other maps and missing material effects remain incomplete.',runs=runtime,staged=staged,tests=dict(passed=7,model_integration_checks=checks,log='outputs/WORLD-083-tests.log'),archive_integrity=dict(path=archive.relative_to(r).as_posix(),sha256=sha(archive),seven_zip_test_exit_code=0),source_images_unchanged=True,visual_inspection=dict(korriban='Authored wall and floor materials visibly differ from the baseline; normal/bump images absent from the staged source are explicitly recorded, geometric normals used and unavailable mask highlights disabled.',ordmantell='Converted debris, structures and ground retained in the regression capture.'),limitations=['Bounded GCW conquest spawn views; no all-map/mode/era/traversal certification.','Source topology must match a complete PSP strip; new unmatched geometry is not inserted.','Scrolling, reflection/refraction, invalid normals and bloom remain unfinished.','Korriban staged source omits 25 referenced normal/bump images.'],sha256={p.relative_to(r).as_posix():sha(p) for p in files})
(r/'outputs/WORLD-083-state.json').write_text(json.dumps(report,indent=2)+'\n')
texture=json.loads((r/'outputs/TEXTURE-RUNTIME-083.json').read_text())
for name in names:
    if name in texture:
        texture[name]['visual_state']=report['visual_inspection']['ordmantell' if 'ordmantell' in name else 'korriban'] if name.startswith('converted') else 'On-foot GCW conquest baseline with global pack 074; no converted MSH bridge.'
        if name.startswith('converted'):texture[name]['world']=runtime[name]['frame_report']
(r/'outputs/TEXTURE-RUNTIME-083.json').write_text(json.dumps(texture,indent=2)+'\n')
print(json.dumps(dict(tests=7,model_checks=checks,korriban=runtime['converted083c-korriban']['frame_report'],ordmantell=runtime['converted083-ordmantell']['frame_report'],binary_sha256=sha(r/'work/build-windows-native/bin/RenegadeNative.exe')),indent=2))
