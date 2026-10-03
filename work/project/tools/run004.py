#!/usr/bin/env python3
"""Run an actual native executable with bounded lifetime and durable diagnostics.
Controller replays and optional stepping affect only buttons/analog samples.
A clean exit is NOT a gameplay-acceptance verdict.
"""
import argparse, hashlib, json, os, signal, subprocess, time
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('name');p.add_argument('--exe',type=Path,required=True)
p.add_argument('--root',type=Path,default=Path('/mnt/data/renegade'))
p.add_argument('--vblanks',type=int,default=3300);p.add_argument('--budget',type=int,default=2000000000)
p.add_argument('--timeout',type=float,default=600);p.add_argument('--start',type=int,default=3000)
p.add_argument('--stride',type=int,default=10);p.add_argument('--replay',type=Path);p.add_argument('--env',action='append',default=[])
a=p.parse_args();r=a.root.resolve();exe=a.exe.resolve();out=r/'runs'/a.name
if a.timeout<=0 or a.timeout>7200 or a.stride<1: p.error('Invalid bound')
if not exe.is_file():p.error('Native executable missing')
out.mkdir(parents=True,exist_ok=False)
def digest(f):
 with f.open('rb') as s:return hashlib.file_digest(s,'sha256').hexdigest()
def save(status):
 temp=out/'run.json.tmp';temp.write_text(json.dumps(status,indent=2)+'\n');temp.replace(out/'run.json')
env={k:v for k,v in os.environ.items() if not k.startswith(('RENEGADE_','PSPRECOMP_'))}
env.update(PSPRECOMP_STOP_VBLANK=str(a.vblanks),PSPRECOMP_FRAME_DUMP_DIR=str(out/'frames'),
 PSPRECOMP_FRAME_DUMP_LIMIT='900',PSPRECOMP_FRAME_DUMP_START=str(a.start),PSPRECOMP_FRAME_DUMP_STRIDE=str(a.stride),
 PSPRECOMP_FRAME_DUMP_DUPLICATES='1',PSPRECOMP_IO_DIAG='1',PSPRECOMP_THREAD_DIAG='1',PSPRECOMP_MPEG_DIAG='1',
 PSPRECOMP_WINDOW='0',PSPRECOMP_AUDIO='1',SDL_AUDIODRIVER='dummy',PSPRECOMP_AUDIO_WAV=str(out/'native-audio.wav'))
if a.replay:
 env['RENEGADE_INPUT_REPLAY']=str(a.replay.resolve());(out/'input-replay.txt').write_bytes(a.replay.read_bytes())
for item in a.env:
 k,sep,v=item.partition('=')
 if not sep or not k.startswith(('PSPRECOMP_','RENEGADE_','SDL_')):p.error('Only runtime diagnostic environment allowed')
 env[k]=v
cmd=[str(exe),str(r/'game/disc/PSP_GAME/SYSDIR/BOOT.BIN'),str(r/'game/disc'),str(a.budget)]
s={'format':'renegade-run-v4','state':'starting','first_level_gameplay_verified':False,'native_binary_sha256':digest(exe),
 'boot_sha256':digest(Path(cmd[1])),'command':cmd,'environment':{k:v for k,v in env.items() if k.startswith(('PSPRECOMP_','RENEGADE_','SDL_'))},
 'timeout_seconds':a.timeout,'timed_out':False,'exit_code':None,'started_unix':time.time()}
save(s);begin=time.monotonic()
with (out/'native.log').open('wb') as log:
 child=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
 s.update(state='running',pid=child.pid);save(s)
 try:s['exit_code']=child.wait(timeout=a.timeout)
 except subprocess.TimeoutExpired:
  s['timed_out']=True;os.killpg(child.pid,signal.SIGKILL);s['exit_code']=child.wait();s['external_stop']='wall-clock timeout SIGKILL'
 except BaseException:
  if child.poll() is None:os.killpg(child.pid,signal.SIGKILL);child.wait()
  s['external_stop']='runner interrupted';raise
 finally:
  s.update(state='finished',elapsed_seconds=round(time.monotonic()-begin,3),frame_count=len(list((out/'frames').glob('*.ppm'))))
  text=(out/'native.log').read_text(errors='replace');s['stop_lines']=[line for line in text.splitlines() if '[renegade] STOP:' in line or '[renegade] ERROR:' in line]
  save(s)
print(json.dumps(s,indent=2))
