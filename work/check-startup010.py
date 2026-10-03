"""Run all 19 preserved native startup/configuration rejection cases on Windows."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,tempfile,time,re
p=argparse.ArgumentParser();p.add_argument('name',nargs='?',default='startup010');a=p.parse_args()
if not re.fullmatch(r'[A-Za-z0-9_-]+',a.name):p.error('Use a simple run name')
r=Path(__file__).resolve().parent
exe=r/'build-windows-native/bin/RenegadeNative.exe'
disc=r/'game/disc';boot=disc/'PSP_GAME/SYSDIR/BOOT.BIN'
out=r/'runs'/a.name
out.mkdir(parents=True,exist_ok=False)
results=[]
with tempfile.TemporaryDirectory(prefix='fixtures-',dir=out) as name:
    tmp=Path(name);empty=tmp/'empty';empty.write_bytes(b'')
    wrong=tmp/'modified';data=bytearray(boot.read_bytes());data[-1]^=1;wrong.write_bytes(data)
    cases=[
        ('missing-boot',tmp/'missing',disc,'1000',{},'BOOT.BIN identity mismatch'),
        ('empty-boot',empty,disc,'1000',{},'BOOT.BIN identity mismatch'),
        ('modified-boot',wrong,disc,'1000',{},'BOOT.BIN identity mismatch'),
        ('wrong-disc',boot,tmp,'1000',{},'Disc-root identity mismatch'),
        ('trailing-budget',boot,disc,'100junk',{},'Dispatch budget must be a positive integer'),
        ('negative-budget',boot,disc,'-1',{},'Dispatch budget must be a positive integer'),
        ('zero-budget',boot,disc,'0',{},'Dispatch budget must be a positive integer'),
        ('resolution',boot,disc,'1000',{'PSPRECOMP_WINDOW':'1','RENEGADE_OUTPUT_RESOLUTION':'99999x99999'},'Unsupported RENEGADE_OUTPUT_RESOLUTION'),
        ('scale',boot,disc,'1000',{'PSPRECOMP_WINDOW':'1','PSPRECOMP_WINDOW_SCALE':'2junk'},'PSPRECOMP_WINDOW_SCALE must be')]
    for n,extra,expected in [
        ('mode',{'RENEGADE_CONTROLS':'unknown'},'RENEGADE_CONTROLS must be'),
        ('left-deadzone',{'RENEGADE_LEFT_DEADZONE':'-1'},'RENEGADE_LEFT_DEADZONE'),
        ('right-deadzone',{'RENEGADE_RIGHT_DEADZONE':'nan'},'RENEGADE_RIGHT_DEADZONE'),
        ('look-x',{'RENEGADE_LOOK_X':'4.1'},'RENEGADE_LOOK_X'),
        ('look-y',{'RENEGADE_LOOK_Y':'abc'},'RENEGADE_LOOK_Y'),
        ('curve',{'RENEGADE_LOOK_CURVE':'0.5'},'RENEGADE_LOOK_CURVE'),
        ('trigger',{'RENEGADE_TRIGGER_THRESHOLD':'1'},'RENEGADE_TRIGGER_THRESHOLD'),
        ('invert',{'RENEGADE_INVERT_Y':'2'},'RENEGADE_INVERT_Y'),
        ('audit-negative',{'RENEGADE_MATERIAL_AUDIT':str(out/'unused.json'),'RENEGADE_MATERIAL_AUDIT_START':'-1'},'Invalid material audit start'),
        ('audit-trailing',{'RENEGADE_MATERIAL_AUDIT':str(out/'unused.json'),'RENEGADE_MATERIAL_AUDIT_START':'10x'},'Invalid material audit start')]:
        cases.append((n,boot,disc,'1000',extra,expected))
    for name,b,d,budget,extra,expected in cases:
        env={k:v for k,v in os.environ.items() if not k.startswith(('PSPRECOMP_','RENEGADE_'))}
        env.update(PSPRECOMP_WINDOW='0',PSPRECOMP_AUDIO='0',SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',RENEGADE_CONTROLS='modern',PSPRECOMP_GE_BACKEND='software')
        env['PATH']=str(r/'windows-sdk/bin')+os.pathsep+env.get('PATH','')
        env.update(extra);begin=time.monotonic()
        try:
            cp=subprocess.run([str(exe),str(b),str(d),budget],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=25,creationflags=subprocess.CREATE_NO_WINDOW)
            text=cp.stdout.decode(errors='replace');code=cp.returncode;timed_out=False
        except subprocess.TimeoutExpired as e:
            text=(e.stdout or b'').decode(errors='replace');code=None;timed_out=True
        (out/(name+'.log')).write_text(text,encoding='utf-8')
        results.append(dict(case=name,exit_code=code,timed_out=timed_out,expected=expected,passed=code==3 and expected in text,seconds=time.monotonic()-begin))
        print(name,results[-1]['passed'],flush=True)
with exe.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
record=dict(native_sha256=digest,cases=results,passed=all(x['passed'] for x in results))
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
raise SystemExit(0 if record['passed'] else 1)
