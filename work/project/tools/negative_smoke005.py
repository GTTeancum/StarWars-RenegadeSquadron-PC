#!/usr/bin/env python3
"""Exercise actual native startup rejection; no fake 'pass' on arbitrary exit."""
import argparse, hashlib, json, os, subprocess, tempfile, time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('/mnt/data/renegade'));a=p.parse_args();r=a.root
exe=r/'intake/out/native004/bin/RenegadeNative';boot=r/'game/disc/PSP_GAME/SYSDIR/BOOT.BIN';disc=r/'game/disc';out=r/'logs/session005/negative';out.mkdir(parents=True,exist_ok=True)
results=[]
with tempfile.TemporaryDirectory(prefix='renegade-negative-') as tmp:
 tmp=Path(tmp);empty=tmp/'empty';empty.write_bytes(b'');wrong=tmp/'modified';data=bytearray(boot.read_bytes());data[-1]^=1;wrong.write_bytes(data)
 cases=[('missing-boot',tmp/'missing',disc,'1000',{},'BOOT.BIN identity mismatch'),('empty-boot',empty,disc,'1000',{},'BOOT.BIN identity mismatch'),('same-size-modified-boot',wrong,disc,'1000',{},'BOOT.BIN identity mismatch'),('wrong-disc-root',boot,tmp,'1000',{},'Disc-root identity mismatch'),('trailing-budget',boot,disc,'100junk',{},'Dispatch budget must be a positive integer'),('negative-budget',boot,disc,'-1',{},'Dispatch budget must be a positive integer'),('zero-budget',boot,disc,'0',{},'Dispatch budget must be a positive integer'),('bad-resolution',boot,disc,'1000',{'PSPRECOMP_WINDOW':'1','RENEGADE_OUTPUT_RESOLUTION':'99999x99999'},'Unsupported RENEGADE_OUTPUT_RESOLUTION'),('bad-scale',boot,disc,'1000',{'PSPRECOMP_WINDOW':'1','PSPRECOMP_WINDOW_SCALE':'2junk'},'PSPRECOMP_WINDOW_SCALE must be')]
 for name,b,d,budget,extra,expected in cases:
  env={k:v for k,v in os.environ.items() if not k.startswith(('PSPRECOMP_','RENEGADE_'))};env.update(PSPRECOMP_WINDOW='0',PSPRECOMP_AUDIO='0',SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy');env.update(extra)
  begin=time.monotonic();cp=subprocess.run([str(exe),str(b),str(d),budget],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=25)
  text=cp.stdout.decode(errors='replace');(out/(name+'.log')).write_text(text);ok=cp.returncode==3 and expected in text
  results.append(dict(case=name,exit_code=cp.returncode,elapsed_seconds=time.monotonic()-begin,expected_error=expected,passed=ok))
record=dict(binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),cases=results,passed=all(c['passed'] for c in results))
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2));raise SystemExit(0 if record['passed'] else 1)
