"""Prepare immutable 101 tools; existing controller stepping needs no native edit."""
from pathlib import Path
root = Path(__file__).resolve().parent.parent
p = root/'work/capture-motion101.py'
assert not p.exists()
s = (root/'work/capture-coverage099.py').read_text()
s = s.replace("args = parser.parse_args()", "parser.add_argument('--retreat',action='store_true',help='Back away and turn after the standard route for a clearer final view')\nargs = parser.parse_args()")
s = s.replace('import argparse, hashlib, json, subprocess, sys',
              'import argparse, hashlib, json, subprocess, sys, time')
s = s.replace('frame = 1400', 'frame = 1400')
s = s.replace("meta=dict(planet=", "spawn_frame=frame\nmotion=[\n    (30,0,0,0,0,0,0,'enable-neutral'),\n    (180,0,24000,0,0,0,0,'forward'),\n    (45,0,0,22000,0,0,0,'look-right'),\n    (90,0,24000,0,0,0,24000,'forward-fire'),\n    (60,-24000,0,0,0,0,24000,'strafe-fire'),\n    (45,0,0,0,0,0,0,'release-settle'),\n]\nassert not menu_stage, 'Motion route requires a spawned scenario'\nframe+=sum(row[0] for row in motion)\ncontrol=root/'work/runs'/('control-'+args.name)\nassert not control.exists()\ncontrol.mkdir()\npad=control/'gamepad.txt'\npad.write_text('1 0 0 0 0 0 0 0 0\\n')\nmeta=dict(spawn_vblank=spawn_frame, motion=motion, input_scope='Existing modern diagnostic sampler and controller-only pause/commands; no guest-state injection', planet=")
s = s.replace("'PSPRECOMP_GE_GPU_HW_TRANSFORM':'0','PSPRECOMP_GE_GPU_HW_CULL':'0'}", "'PSPRECOMP_GE_GPU_HW_TRANSFORM':'0','PSPRECOMP_GE_GPU_HW_CULL':'0',\n     'RENEGADE_CONTROLS':'modern','RENEGADE_TRACE_ACTIONS':'1','RENEGADE_TRACE_CONTEXTS':'1',\n     'RENEGADE_GAMEPAD_DIAGNOSTIC':str(pad),\n     'RENEGADE_CONTROL_START':str(spawn_frame),'RENEGADE_CONTROL_DIRECTORY':str(control)}")
s = s.replace("raise SystemExit(subprocess.call(cmd,cwd=root))", '''
runner=subprocess.Popen(cmd,cwd=root)
def wait_pause(target):
    deadline=time.monotonic()+840
    while time.monotonic()<deadline:
        if runner.poll() is not None:
            raise RuntimeError(f'Runner terminated before pause {target}: {runner.returncode}')
        try:
            st=json.loads((control/'status.json').read_text())
            if st['paused'] and st['vblank']==target:
                return st
        except (OSError,json.JSONDecodeError):
            pass
        time.sleep(.1)
    raise TimeoutError(f'Pause {target} not reached; existing runner retains its own lifetime bound')
def publish(path,text):
    temp=path.with_suffix('.next');temp.write_text(text)
    deadline=time.monotonic()+5
    while True:
        try: temp.replace(path);return
        except PermissionError:
            if time.monotonic()>deadline:raise
            time.sleep(.01)
current=spawn_frame
wait_pause(current)
for index,(frames,lx,ly,rx,ry,lt,rt,label) in enumerate(motion,1):
    end=current+frames
    sample=f'{index+1} 1 {lx} {ly} {rx} {ry} {lt} {rt} 0\\n'
    publish(pad,sample)
    record=dict(start=current,end=end,frames=frames,label=label,sequence=index,
                pad_sample=sample.strip(),lx=lx,ly=ly,rx=rx,ry=ry,lt=lt,rt=rt)
    with (control/'adaptive101.jsonl').open('a') as f:f.write(json.dumps(record)+'\\n')
    # The final command extends past the stop so the native does not pause before exiting.
    until=end+1 if index==len(motion) else end
    publish(control/'command.txt',f'{index} {until} 0 128 128\\n')
    print(json.dumps(record),flush=True)
    if index<len(motion):wait_pause(end)
    current=end
assert current==frame
raise SystemExit(runner.wait())
''')
p.write_text(s)
s=s.replace("assert not menu_stage, 'Motion route requires a spawned scenario'", """assert not menu_stage, 'Motion route requires a spawned scenario'
if args.retreat:
    motion += [(120,0,-24000,0,0,0,0,'backward-retreat'),
               (30,0,0,-22000,0,0,0,'look-left'),
               (45,0,0,0,0,0,0,'final-settle')]""")
p.write_text(s)
print('Prepared modern dual-stick movement/fire capture tool 101; native source unchanged.')
