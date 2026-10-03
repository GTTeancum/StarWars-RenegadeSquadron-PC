"""Verify fresh before/after routes, native loading and resolution evidence."""
import hashlib, json, re
from pathlib import Path
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
pack_path=root/'outputs/TEXTURE-PACK-106-ui2.json'
pack={r['id']:r for r in json.loads(pack_path.read_text())['files']}
expected={'mygeeto-clone':'ENVS/PREQUEL/MYGEETO.PSP', 'hoth-gcw':'ENVS/CLASSIC/HOTH.PSP',
          'space-kashyyyk-gcw':'ENVS/CLASSIC/SPACE_KASHYYYK_CIVIL.PSP'}
results=[]
for scenario,archive in expected.items():
    names=[f'textures106-{scenario}-{phase}-gpu' for phase in ['before','after-ui2']]
    states=[]; inspections=[]; logs=[]; artifacts={}
    for name in names:
        folder=root/'work/runs'/name
        state=json.loads((folder/'run.json').read_text());states.append(state)
        assert state['state']=='finished' and state['exit_code']==0 and not state['timed_out']
        assert sha(folder/'native/RenegadeNative.exe')==state['native_binary_sha256']=='9c6f1e06072ee083fadb17d2cb9b26069d4601747f23590c72128d9110596659'
        inspection=json.loads((root/'outputs'/f'{name}-inspection.json').read_text());inspections.append(inspection)
        assert archive in inspection['actual_opens'], (name,inspection['actual_opens'])
        for rel,digest in inspection['artifact_sha256'].items():assert sha(root/rel)==digest;artifacts[rel]=digest
        env=state['environment']
        assert env['RENEGADE_FXAA']=='1' and env['PSPRECOMP_WINDOW']=='0' and env['RENEGADE_OUTPUT_RESOLUTION']=='1280x720'
        assert env['PSPRECOMP_CONFIG'].endswith('dx12-preview.ini')
        assert Image.open(root/'outputs'/f'{name}-fxaa.png').size==(1280,720)
        logs.append((folder/'native.log').read_text(errors='replace'))
        assert f'[gpu-internal-frame] vblank={int(env["PSPRECOMP_STOP_VBLANK"])-1} resolution=1280x720' in logs[-1]
    assert states[0]['boot_sha256']==states[1]['boot_sha256']
    assert sha(Path(states[0]['environment']['RENEGADE_INPUT_REPLAY']))==sha(Path(states[1]['environment']['RENEGADE_INPUT_REPLAY']))
    assert inspections[0]['stop_vblank']==inspections[1]['stop_vblank']
    assert states[1]['environment']['RENEGADE_OVERRIDE_ROOT']==str(root/'work/mods-upscale106-ui2')
    loaded=sorted(set(re.findall(r'\[overrides\] texture (tex-v1-[0-9a-f]{64}) loaded',logs[1])))
    assert loaded and all(id_ in pack for id_ in loaded)
    generated=[id_ for id_ in loaded if pack[id_]['method']!='preferred_authored_source']
    authored=[id_ for id_ in loaded if pack[id_]['method']=='preferred_authored_source']
    assert generated
    probes=[]
    report=root/'work/runs'/names[1]/'render-report.jsonl';artifacts[report.relative_to(root).as_posix()]=sha(report)
    for line in report.read_text().splitlines():
        for p in json.loads(line)['probes']:
            if p['id'] in pack:
                assert [p['replacement_width'],p['replacement_height']]==pack[p['id']]['output_size'],p
                if pack[p['id']]['method']!='preferred_authored_source':
                    assert p['replacement_width']==p['width']*4 and p['replacement_height']==p['height']*4
                probes.append(p)
    assert any(p['layer']=='scene' for p in probes) and any(p['layer']=='overlay' for p in probes)
    stats=re.findall(r'\[ge-backend-result\] ([^\r\n]+)',logs[1]);assert stats
    last=dict(re.findall(r'(\w+)=([^ ]+)',stats[-1]));assert last['missing_textures']=='0' and int(last['replacement_draws'])>0
    before=np.asarray(Image.open(root/'outputs'/f'{names[0]}-fxaa.png')).astype(int)
    after=np.asarray(Image.open(root/'outputs'/f'{names[1]}-fxaa.png')).astype(int)
    diff=np.abs(after-before)
    assert np.any(diff)
    results.append(dict(scenario=scenario,archive=archive,stop_vblank=inspections[1]['stop_vblank'],
        loaded_ids=loaded,generated_loaded=len(generated),authored_loaded=len(authored),probe_samples=len(probes),
        terminal_gpu_stats=last,changed_screen_pixels=int(np.any(diff,axis=2).sum()),mean_screen_channel_difference=float(diff.mean()),
        artifact_sha256=artifacts,
        comparison_scope='Identical replay/native/config and diagnostic boundary; game timing/actors are not guaranteed pixel-identical. Screen difference is supporting evidence, not texture-only attribution.'))
out=dict(pack_sha256=sha(pack_path),scenarios=results,
    scope='Bounded ground/Clone Wars/GCW/space spawn diagnostics, loading and720p raw/FXAA evidence. No full matches, flight, physical controller or every-map visual acceptance.')
p=root/'outputs/UPSCALER-106-gameplay.json'
if p.exists():assert json.loads(p.read_text())==out
else:p.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({r['scenario']:{k:r[k] for k in ['generated_loaded','authored_loaded','probe_samples','terminal_gpu_stats']} for r in results},indent=2))
