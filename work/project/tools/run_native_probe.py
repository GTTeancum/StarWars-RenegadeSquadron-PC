#!/usr/bin/env python3
"""Fallback diagnostic: execute generated game code without title services.
A probe is not gameplay and cannot replace the full native host.
"""
from pathlib import Path
import json,os,subprocess,time,hashlib
root=Path('/mnt/data/renegade');r=root/'intake/sources/PSPRecomp';p=r/'profiles/renegade';logs=root/'logs';out=root/'probe-status.json'
result={'first_level_gameplay_verified':False,'probe_only':True}
def save():out.write_text(json.dumps(result,indent=2))
try:
 deadline=time.monotonic()+1000
 while time.monotonic()<deadline:
  s=root/'build-status.json'
  if s.exists():
   data=json.loads(s.read_text());stages=data.get('stages',[])
   if stages and stages[-1]['stage'] in ('stopped','native-run'):break
  time.sleep(3)
 else:raise RuntimeError('Full host build has not reached a bounded stopping point; avoiding concurrent builds')
 if not (p/'generated/generated_registry.cpp').exists():raise RuntimeError('No generated registry is present')
 code='''#include "psprecomp/elf32.hpp"
#include "psprecomp/runtime.hpp"
#include <iostream>
#include <memory>
namespace psprecomp { void register_generated_functions(Runtime&); }
int main(int argc,char** argv) {
 if(argc!=2) return 2;
 auto runtime=std::make_unique<psprecomp::Runtime>();auto& rt=*runtime;
 try {
  auto image=psprecomp::Elf32Image::from_file(argv[1]);
  image.load_and_relocate(rt.memory());
  psprecomp::register_generated_functions(rt);
  rt.cpu().gpr[28]=0;rt.cpu().gpr[29]=0x09ffff00u;rt.cpu().gpr[31]=0;
  std::cerr<<"[native-probe] Executing generated ULUS10292 MIPS code as host C++; no PSP service layer installed.\\n";
  rt.run(image.runtime_entry(),10000);
  std::cerr<<"[native-probe] STOP: "<<rt.stop_reason()<<" pc=0x"<<std::hex<<rt.cpu().pc<<"\\n";
  return 0;
 } catch(const std::exception& e) {std::cerr<<"[native-probe] ERROR: "<<e.what()<<"\\n";return 3;}
}
'''
 (p/'host/probe.cpp').write_text(code)
 cm=p/'CMakeLists.txt';text=cm.read_text()
 if 'add_executable(RenegadeProbe' not in text:
  cm.write_text(text+'\nadd_executable(RenegadeProbe host/probe.cpp)\ntarget_link_libraries(RenegadeProbe PRIVATE renegade_aot psprecomp_core)\nset_target_properties(RenegadeProbe PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")\n')
 b=root/'intake/out/renegade'
 with (logs/'build-probe.log').open('w') as f:
  x=subprocess.run(['cmake','--build',str(b),'--target','RenegadeProbe','--parallel','4'],stdout=f,stderr=subprocess.STDOUT,timeout=900)
 result['build_exit_code']=x.returncode;save()
 if x.returncode:raise RuntimeError('Probe compile/link failed; see build-probe.log')
 exe=b/'bin/RenegadeProbe';result['binary_sha256']=hashlib.sha256(exe.read_bytes()).hexdigest()
 boot=root/'game/disc/PSP_GAME/SYSDIR/BOOT.BIN'
 assert hashlib.sha256(boot.read_bytes()).hexdigest()=='f4c7a9ef93475fc8017f649346ef79b599649dc47462ec419e9fd373146f8c68'
 with (logs/'native-probe.log').open('w') as f:
  x=subprocess.run([str(exe),str(boot)],stdout=f,stderr=subprocess.STDOUT,timeout=30)
 result['run_exit_code']=x.returncode
 result['output']=(logs/'native-probe.log').read_text(errors='replace')[-5000:]
except Exception as e:result['stopped_reason']=str(e)
finally:save();print(json.dumps(result,indent=2),flush=True)
