from pathlib import Path
import json, hashlib
root = Path(r'D:\Programming\GitHub\RenegadeSquadronPC')
work = root/'work'
out = root/'outputs'
exe = work/'build-windows-native'/'bin'/'RenegadeNative.exe'
exe_hash = hashlib.sha256(exe.read_bytes()).hexdigest()
old_crash = 'Unsupported Allegrex instruction 0x00000000 at 0x08A2E2E4: invalid internal function entry'
scenarios = [
    dict(id='a', old_run='instant015a', run='instant016a', map='Boz Pity', era='Galactic Civil War', mode='Conquest', evidence_frame='instant016a-vblank2640.png', final_vblank=2640, status='live ground gameplay'),
    dict(id='b', old_run='instant015b', run='instant016b', map='Geonosis', era='Clone Wars', mode='Conquest', evidence_frame='instant016b-vblank2576.png', final_vblank=2576, status='live ground gameplay'),
    dict(id='c', old_run='instant015c', run='instant016c_flight', map='Space Coruscant', era='Clone Wars', mode='Assault', evidence_frame='instant016c_flight-vblank2784.png', final_vblank=2784, status='live space hangar gameplay'),
    dict(id='d', old_run='instant015d', run='instant016d', map='Space Alderaan', era='Galactic Civil War', mode='1-Flag CTF', evidence_frame='instant016d-vblank2784.png', final_vblank=2784, status='live space hangar gameplay'),
    dict(id='e', old_run='instant015e', run='instant016e', map='Echo Base', era='Galactic Civil War', mode='2-Flag CTF', evidence_frame='instant016e-vblank2640.png', final_vblank=2640, status='live ground gameplay'),
    dict(id='f', old_run='instant015f', run='instant016f', map='Kashyyyk', era='Clone Wars', mode='Hero CTF', evidence_frame='instant016f-vblank2656.png', final_vblank=2656, status='live ground gameplay'),
]
rows=[]
for s in scenarios:
    run_json = work/'runs'/s['run']/'run.json'
    state = json.loads(run_json.read_text())
    summary_path = out/f"{s['run']}-summary.json"
    img = out/s['evidence_frame']
    rows.append({
        **s,
        'old_baseline_crash': old_crash,
        'new_run_json': str(run_json),
        'new_summary_json': str(summary_path) if summary_path.exists() else None,
        'evidence_image': str(img),
        'evidence_image_sha256': hashlib.sha256(img.read_bytes()).hexdigest(),
        'exit_code': state.get('exit_code'),
        'timed_out': state.get('timed_out'),
        'elapsed_seconds': state.get('elapsed_seconds'),
        'stop_lines': state.get('stop_lines'),
        'native_binary_sha256': state.get('native_binary_sha256') or exe_hash,
    })
result = {
    'checkpoint': '016',
    'project_root': str(root),
    'binary': {'path': str(exe), 'bytes': exe.stat().st_size, 'sha256': exe_hash},
    'shared_fixed_crash': old_crash,
    'source_changes': [
        'work/project/source/profiles/renegade/supplemental/callback_08896118.cpp',
        'work/project/source/profiles/renegade/tests/platform003.cpp',
        'work/instant016_runner.py',
    ],
    'test_results': {
        'build_windows_RenegadeNative_exit': int((work/'build-windows016-incremental.exit').read_text().strip()),
        'renegade_platform_tests_exit': int((work/'test-platform016.exit').read_text().strip()),
        'renegade_platform_tests_summary': 'PASS 288 platform/printf/callback/PSMF checks',
        'test_windows_exit': int((work/'test-windows016.exit').read_text().strip()),
        'test_windows_summary': '18/19 passed; renegade_savedata_io_tests is the known Windows symlink privilege failure',
        'startup016_summary': '19/19 startup checks passed',
    },
    'instant_action_scenarios': rows,
    'limitations': [
        'Scripted replays reached spawn/live gameplay or live space hangar gameplay and then stopped by diagnostic command.',
        'This does not prove full match duration, every Instant Action map/mode, real controller hardware, multiplayer, or ship takeoff/combat.',
        'The first Space Coruscant helper pass reached the space spawn map only; instant016c_flight is the gameplay evidence run.',
    ],
    'dependencies_missing': [],
}
path = out/'INSTANT-ACTION-016-results.json'
path.write_text(json.dumps(result, indent=2) + '\n')
print(path)
print(hashlib.sha256(path.read_bytes()).hexdigest())
