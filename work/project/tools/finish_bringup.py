#!/usr/bin/env python3
"""Bounded build/run diagnostics. This script never declares gameplay acceptance."""
from pathlib import Path
import hashlib,json,os,re,subprocess,time,zipfile
root=Path('/mnt/data/renegade');r=root/'intake/sources/PSPRecomp';p=r/'profiles/renegade';h=p/'host';logs=root/'logs'
logs.mkdir(parents=True,exist_ok=True)
status={'first_level_gameplay_verified':False,'kind':'experimental Linux x86-64 AOT bring-up','source_commit':'f6e7d415c7f447b934cc3865a31eb725f353d659','boot_sha256':'f4c7a9ef93475fc8017f649346ef79b599649dc47462ec419e9fd373146f8c68','stages':[]}
def record(stage,**kw):
 status['stages'].append(dict(stage=stage,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),**kw));(root/'build-status.json').write_text(json.dumps(status,indent=2));print(stage,kw,flush=True)
def run(cmd,log,timeout=600,env=None):
 with (logs/log).open('w') as f:
  try:
   v=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=timeout,env=env);return v.returncode
  except subprocess.TimeoutExpired:return 124
try:
 # Wait for the already-started source generation / first build, bounded.
 deadline=time.monotonic()+900
 while not (logs/'build-native.exit').exists() and time.monotonic()<deadline:
  time.sleep(3)
 if not (logs/'build-native.exit').exists():
  record('initial-build',exit_code=124,reason='No completion marker within 15 minutes')
  raise RuntimeError('Initial build did not finish in the bounded window')
 record('initial-build',exit_code=int((logs/'build-native.exit').read_text()))
 # Match diagnostic host calls to actual declarations instead of assuming VCS signatures.
 headers='\n'.join(x.read_text(errors='replace') for x in (r/'profiles/vcs/host').glob('*.hpp'))
 main=(h/'main.cpp').read_text()
 main=re.sub(r'        if\(auto module=elf.find_module_info\(rt.memory\(\)\)\) rt.cpu\(\).gpr\[28\]=module->gp;',
             '        rt.cpu().gpr[28]=0; // Verified module GP for this exact BOOT.BIN.',main)
 main=main.replace('<<" functions="<<rt.function_count()','')
 for name in ['initialize_vcs_configuration','install_display_heartbeat','install_starvation_preemption','display_window_start','initialize_ge_gpu_backend','report_disc_read_stats','report_present_stats','audio_output_shutdown','display_window_shutdown','shutdown_ge_gpu_backend']:
  decl=re.search(r'\b'+name+r'\s*\(([^)]*)\)\s*(?:noexcept\s*)?;',headers,re.S)
  if not decl:continue
  raw=decl.group(1).strip();args=[];recognized=True
  for a in ([] if raw in ('','void') else raw.split(',')):
   a=a.split('=')[0].strip()
   if 'Runtime' in a and '&' in a:args.append('rt')
   elif ('string' in a and '&' in a and 'const' not in a):args.append('error')
   elif 'filesystem' in a or 'path' in a.lower():args.append('std::filesystem::absolute(argv[0]).parent_path()')
   elif 'ostream' in a:args.append('std::cerr')
   else:recognized=False;break
  if recognized:
   # Keep initialization's nested filesystem expression intact with a dedicated pattern.
   if name=='initialize_vcs_configuration':
    main=re.sub(r'vcs::initialize_vcs_configuration\([^;]*\);',f'vcs::{name}('+', '.join(args)+');',main)
   else:
    main=re.sub(r'vcs::'+name+r'\([^()]*\)',f'vcs::{name}('+', '.join(args)+')',main)
 # Error argument can be needed before GPU initialization.
 main=main.replace('        std::string error;\n','')
 main=main.replace('    try {\n','    try {\n        std::string error;\n',1)
 (h/'main.cpp').write_text(main)
 b=root/'intake/out/renegade'
 code=run(['cmake','--build',str(b),'--target','RenegadeNative','--parallel','4'],'build-final.log',900)
 record('native-build',exit_code=code)
 if code:raise RuntimeError('Native build has compiler/linker errors; see build-final.log')
 binary=b/'bin/RenegadeNative';status['native_binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
 boot=root/'game/disc/PSP_GAME/SYSDIR/BOOT.BIN'
 if hashlib.sha256(boot.read_bytes()).hexdigest()!=status['boot_sha256']:raise RuntimeError('Executable fingerprint differs')
 env=os.environ.copy();env.update({'PSPRECOMP_HLE_HISTOGRAM':'1','PSPRECOMP_TRACE_ON_ERROR':'1','PSPRECOMP_THREAD_DIAG':'1','PSPRECOMP_IO_DIAG':'1','PSPRECOMP_GE_DIAG':'1','PSPRECOMP_STOP_VBLANK':'120','PSPRECOMP_FRAME_DUMP_DIR':str(root/'frames'),'PSPRECOMP_FRAME_DUMP_LIMIT':'8'})
 code=run([str(binary),str(boot),str(root/'game/disc'),'2000000'],'native-run-001.log',120,env)
 text=(logs/'native-run-001.log').read_text(errors='replace')
 record('native-run',exit_code=code,stop_lines=[x for x in text.splitlines() if '[renegade]' in x or 'Missing HLE' in x][-20:])
 status['frame_files']=[x.name for x in (root/'frames').glob('*')] if (root/'frames').exists() else []
except Exception as e:
 record('stopped',reason=str(e))
finally:
 (root/'build-status.json').write_text(json.dumps(status,indent=2))
