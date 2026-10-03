"""Preserve verified early terminal outcomes while remaining map checks run."""
import hashlib,json,re
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
expected={'coverage102-geonosis-era-menu':None,
          'coverage102-geonosis-gcw-gpu':'ENVS/CLASSIC/GEONOSIS.PSP',
          'coverage102-mustafar-clone-gpu':'ENVS/PREQUEL/MUSTAFAR.PSP',
          'coverage102-korriban-clone-gpu':'ENVS/PREQUEL/KORRIBAN.PSP',
          'coverage102-saleucami-clone-gpu':'ENVS/PREQUEL/SALEUCAMI.PSP'}
rows=[]
for name,archive in expected.items():
    folder=root/'work/runs'/name;state=json.loads((folder/'run.json').read_text())
    assert state['state']=='finished' and state['exit_code']==0 and not state['timed_out'],name
    assert state['native_binary_sha256']==sha(folder/'native/RenegadeNative.exe')=='924ae90a2ed8141bb418df07203100912bb08176eb987b3a834819a49a68e2ec'
    env=state['environment'];stop=int(env['PSPRECOMP_STOP_VBLANK']);log=(folder/'native.log').read_text(errors='replace')
    opens={m[1].replace('\\','/') for line in log.splitlines() if '[io] raw UMD open' in line
           for m in [re.search(r'[\\/]((?:ENVS|GUIMENU|GRAPHICS|MISC)[\\/][^"\r\n]+)"',line)] if m}
    if archive:assert archive in opens,(name,archive)
    assert f'VBlank diagnostic stop at {stop} ' in log
    assert env['RENEGADE_OUTPUT_RESOLUTION']=='1280x720' and env['RENEGADE_FXAA']=='1' and env['PSPRECOMP_WINDOW']=='0'
    gpu=env['PSPRECOMP_GE_BACKEND']=='directx12'
    raw=folder/'gpu.ppm' if gpu else folder/f'frames/render-720p/frame_{stop-1:06d}.ppm'
    fxaa=folder/'gpu-fxaa.ppm' if gpu else folder/f'frames/render-720p-fxaa/frame_{stop-1:06d}.ppm'
    assert Image.open(raw).size==Image.open(fxaa).size==(1280,720)
    result=re.search(r'\[ge-backend-result\] (.*)',log);assert result
    assert re.search(r'\bmissing_textures=0\b',result[1])
    rows.append(dict(name=name,expected_archive=archive,stop_vblank=stop,elapsed_seconds=state['elapsed_seconds'],
                     actual_opens=sorted(opens),terminal_exit=0,timed_out=False,dimensions=[1280,720],
                     artifact_sha256={p.relative_to(root).as_posix():sha(p) for p in [folder/'run.json',folder/'native.log',raw,fxaa]}))
p=root/'outputs/COVERAGE-102-progress.json';assert not p.exists()
report=dict(scope='First five terminal/hash/open/dimension checks only; full original-identity/capture/catalog verification pending.',runs=rows)
p.write_text(json.dumps(report,indent=2)+'\n')
lines=['# Checkpoint 102 — first five completed checks','',
       'Goal remains active/incomplete. Four new gameplay variants and the Geonosis era-menu probe reached requested stops, exit 0, no timeout. Native identities, actual archive opens, headless 1280×720/FXAA dimensions and zero missing-texture counters were verified. Full original-ID, lossless PNG and final catalog validation remain pending.','',
       '| Run | Actual expected archive opened | Stop | Seconds |','| --- | --- | ---: | ---: |']
lines += [f"| {r['name']} | {r['expected_archive'] or 'Era menu'} | {r['stop_vblank']} | {r['elapsed_seconds']:.3f} |" for r in rows]
lines += ['',f'- COVERAGE-102-progress.json SHA-256: `{sha(p)}`',
          '- Native SHA-256: `924ae90a2ed8141bb418df07203100912bb08176eb987b3a834819a49a68e2ec`','',
          'Yavin IV and Ord Mantell checks are running; Sullust is next. Expected archive paths alone are not success evidence. These are spawn probes, not completed matches/traversal. Native source and authored image orientation/channels remain unchanged. Mipmap/filtering work stays skipped; no automatic matching/upscales or new bindings. All 102 final results and source snapshot remain pending.','']
(root/'outputs/CHECKPOINT-102-progress2.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'verified_completed_runs':len(rows),'progress_sha256':sha(p),'remaining':'Yavin IV, Ord Mantell, Sullust; final dumps/catalog/visual/source verification'},indent=2))
