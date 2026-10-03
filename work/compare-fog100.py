"""Verify retained pre-fog captures and paired replay/config comparability."""
import hashlib,json
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.file_digest((root/p).open('rb'),'sha256').hexdigest()
old=json.loads((root/'outputs/COVERAGE-096.json').read_text())
new=json.loads((root/'outputs/COVERAGE-100.json').read_text())
rows=[]
for suffix in ['hoth-gcw','mygeeto-clone']:
    before=f'coverage096-{suffix}-software'
    after=f'coverage100-{suffix}-software'
    gpu=f'coverage100-{suffix}-gpu'
    run_rows={name:next(r for r in report['runs'] if r['name']==name)
              for name,report in [(before,old),(after,new),(gpu,new)]}
    states={name:json.loads((root/'work/runs'/name/'run.json').read_text()) for name in run_rows}
    replays={name:sha(f'work/runs/{name}/input-replay.txt') for name in run_rows}
    assert len(set(replays.values()))==1
    assert len({s['environment']['PSPRECOMP_STOP_VBLANK'] for s in states.values()})==1
    assert len({s['boot_sha256'] for s in states.values()})==1
    for name,state in states.items():
        assert state['state']=='finished' and state['exit_code']==0 and not state['timed_out']
        assert sha(f'work/runs/{name}/native/RenegadeNative.exe')==state['native_binary_sha256']
        assert state['environment']['RENEGADE_OUTPUT_RESOLUTION']=='1280x720'
        assert state['environment']['RENEGADE_FXAA']=='1'
        assert state['environment']['RENEGADE_OVERRIDE_ROOT'].endswith('mods-textures-source074')
    for name in [before,after]:
        config='work/rendering/software.ini'
        assert sha(config)==run_rows[name]['artifact_sha256'][config]
    screenshots={}
    for name,report in [(before,old),(after,new),(gpu,new)]:
        p=f'outputs/{name}-fxaa.png'
        assert sha(p)==report['screenshot_sha256'][p]
        assert Image.open(root/p).size==(1280,720)
        screenshots[p]=sha(p)
    rows.append(dict(scenario=suffix, same_controller_replay_sha256=replays[before],
                     same_stop_vblank=run_rows[after]['stop_vblank'],
                     before_native_sha256=states[before]['native_binary_sha256'],
                     after_native_sha256=states[after]['native_binary_sha256'],
                     before_capture=f'outputs/{before}-fxaa.png',after_capture=f'outputs/{after}-fxaa.png',
                     gpu_capture=f'outputs/{gpu}-fxaa.png',screenshot_sha256=screenshots))
report=dict(scope='Same controller inputs, stop, BOOT, output settings and unchanged software config/pack. AI positions, reinforcements and scene timing vary between executions; not deterministic whole-frame pixel parity or independent PSP acceptance.',
            baseline_coverage_sha256=sha('outputs/COVERAGE-096.json'),
            current_coverage_sha256=sha('outputs/COVERAGE-100.json'),comparisons=rows)
(root/'outputs/FOG-100-comparisons.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
