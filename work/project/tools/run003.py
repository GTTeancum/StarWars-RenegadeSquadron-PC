#!/usr/bin/env python3
"""Bounded native test; exit 0 never grants gameplay acceptance automatically."""
import argparse,os,json,subprocess,hashlib,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--vblanks',type=int,default=600);p.add_argument('--budget',type=int,default=100000000);p.add_argument('--timeout',type=int,default=180);p.add_argument('--start',type=int,default=0);p.add_argument('--stride',type=int,default=20);p.add_argument('--replay');p.add_argument('--env',action='append',default=[]);a=p.parse_args()
r=Path('/mnt/data/renegade');exe=r/'intake/out/renegade/bin/RenegadeNative';out=r/'runs'/a.name;out.mkdir(parents=True,exist_ok=False)
env=dict(os.environ);env.update({'PSPRECOMP_STOP_VBLANK':str(a.vblanks),'PSPRECOMP_FRAME_DUMP_DIR':str(out/'frames'),'PSPRECOMP_FRAME_DUMP_LIMIT':'600','PSPRECOMP_FRAME_DUMP_START':str(a.start),'PSPRECOMP_FRAME_DUMP_STRIDE':str(a.stride),'PSPRECOMP_FRAME_DUMP_DUPLICATES':'1','PSPRECOMP_IO_DIAG':'1','PSPRECOMP_THREAD_DIAG':'1','PSPRECOMP_MPEG_DIAG':'1','PSPRECOMP_WINDOW':'0','PSPRECOMP_AUDIO':'1','SDL_AUDIODRIVER':'dummy','PSPRECOMP_AUDIO_WAV':str(out/'native-audio.wav')})
if a.replay:env['RENEGADE_INPUT_REPLAY']=str(Path(a.replay).resolve());(out/'input-replay.txt').write_bytes(Path(a.replay).read_bytes())
for item in a.env:
 k,v=item.split('=',1);env[k]=v
cmd=[str(exe),str(r/'game/disc/PSP_GAME/SYSDIR/BOOT.BIN'),str(r/'game/disc'),str(a.budget)]
status={'native_binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'command':cmd,'environment':{k:v for k,v in env.items() if k.startswith(('PSPRECOMP_','RENEGADE_','SDL_'))},'first_level_gameplay_verified':False,'timeout':False}
t=time.monotonic()
with (out/'native.log').open('wb') as f:
 try:status['exit_code']=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=a.timeout).returncode
 except subprocess.TimeoutExpired:status['exit_code']=None;status['timeout']=True
status['elapsed_seconds']=time.monotonic()-t;status['frame_count']=len(list((out/'frames').glob('*.ppm')))
text=(out/'native.log').read_text(errors='replace');status['stop_lines']=[l for l in text.splitlines() if '[renegade] STOP:' in l or '[renegade] ERROR:' in l]
(out/'run.json').write_text(json.dumps(status,indent=2));print(json.dumps(status,indent=2))
