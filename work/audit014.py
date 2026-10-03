from pathlib import Path
import hashlib,json,zipfile,time
r=Path(__file__).resolve().parent;o=r.parent/'outputs'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
inputs=[
 (Path(r'C:/Users/LRPC/Downloads/Star Wars - Battlefront - Renegade Squadron (USA).7z'),'25273ebd41d5c1721d45ce61d47ed42849b16bb46d953d90458f1bd1ed31bd3e'),
 (Path(r'C:/Users/LRPC/Downloads/RenegadeSquadron-Checkpoint-009-Controls.zip'),'967986e81e2437fe45ddf44ebbb4f3147336cbf52868fc1c47b67f7441d60e19'),
 (r/'game/Star Wars - Battlefront - Renegade Squadron (USA).iso','92d2da6c0a0a689ef5d04475a3c63b80d8e86d6bc4688dbde4adb06b24220326'),
 (r/'build-windows-native/bin/RenegadeNative.exe','7f1d901960d519253cd391e692d2c07524ed40bd9bf9aac1fc778fc2c4c27080')]
verified=[]
for p,expected in inputs:
 actual=sha(p);assert actual==expected,p
 verified.append(dict(path=str(p),bytes=p.stat().st_size,sha256=actual))
source=json.loads((o/'RECOVERY-013-source-and-dependencies.json').read_text())
for row in source['source']:assert sha(r/'project/source'/row['path'])==row['sha256'],row['path']
archive=o/'RenegadeSquadron-Recovery-013-Windows-Source.zip'
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 manifest=json.loads(z.read('manifest010.json'))
 for f in manifest['files']:assert hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256']
run=json.loads((r/'runs/native013a/run.json').read_text());assert run['exit_code']==0 and not run['timed_out']
assert run['native_binary_sha256']==inputs[-1][1]
startup=json.loads((r/'runs/startup013/results.json').read_text());assert len(startup['cases'])==19 and all(c['passed'] for c in startup['cases'])
assert startup['native_sha256']==inputs[-1][1]
tests=(r/'test-windows013.log').read_text();assert '1 tests failed out of 19' in tests and 'renegade_savedata_io_tests' in tests
rows=[json.loads(x) for x in (r/'runs/control-native013a/adaptive011.jsonl').read_text().splitlines()]
assert rows[0]['start']==4252 and rows[-1]['end']==14498
assert all(a['end']==b['start'] for a,b in zip(rows,rows[1:]))
assert all(x.get('psp_x',128)==128 and x.get('psp_y',128)==128 for x in rows)
frames={}
for v in (6606,7938,7979,8099,9948,10554,11168,11348,12383,13306,13843,14018,14178,14498):
 p=o/f'native013a-vblank{v}.png';frames[str(v)]=dict(file=p.name,sha256=sha(p))
result=dict(audit_unix=time.time(),verified_inputs=verified,source_files_unchanged=len(source['source']),source_archive_payloads_verified=len(manifest['files']),native_exit_code=0,native_timed_out=False,startup_cases_passed=19,regression_targets_passed=18,regression_targets_total=19,known_test_failure='savedata_io: Windows symbolic-link privilege missing',adaptive_rows=len(rows),adaptive_contiguous=True,adaptive_original_analog_neutral=True,
 gameplay_acceptance=dict(method='Direct visual inspection by assistant of native framebuffer PNGs plus recorded controller inputs and trace; not inferred from process exit',first_mission_victory_verified=True,victory_vblank=14498,run='native013a',modern_gameplay=True,original_menu_navigation=True,normal_respawns=2,deterministic_replay_claimed=False,physical_controller_end_to_end_verified=False,turret_exit_live_verified=False),frames=frames,
 runner_metadata_note='run.json first_level_gameplay_verified is a conservative runner default. This separate reviewed acceptance record supplies the visual gameplay verdict without rewriting raw runner output.')
(o/'ACCEPTANCE-014.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('frames','verified_inputs')}))
