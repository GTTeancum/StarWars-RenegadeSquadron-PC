"""Remove one hook, invoke a direct incremental build, verify auto-restoration.

Run via test-asset-hook-build030.cmd to inherit the MSVC environment. Original
bytes are restored even if CMake fails; no other generated changes are discarded.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
root=Path(__file__).resolve().parent.parent
profile=root/'work/project/source/profiles/renegade'
unit=profile/'generated/generated_unit_0019.cpp'
original=unit.read_bytes()
newline=b'\r\n' if b'\r\n' in original else b'\n'
call=b'    renegade::render_trace024::name(rt, ctx);'+newline
include=b'#include "../host/render_resource_trace024.hpp"'+newline
assert original.count(call)==original.count(include)==1
report={'original_sha256':hashlib.sha256(original).hexdigest()}
try:
    unit.write_bytes(original.replace(call,b'').replace(include,b''))
    result=subprocess.run([str(root/'work/build-tools/cmake/data/bin/cmake.exe'),'--build',
        str(root/'work/build-windows-native'),'--target','RenegadeNative','--parallel','2'],
        capture_output=True,text=True)
    report.update(exit_code=result.returncode,output=result.stdout+result.stderr,
                  restored_sha256=hashlib.sha256(unit.read_bytes()).hexdigest())
    report['passed']=result.returncode==0 and unit.read_bytes()==original and '1 files updated' in report['output']
finally:
    if unit.read_bytes()!=original:unit.write_bytes(original)
(root/'outputs/AOT-030-build-test.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
sys.exit(0 if report['passed'] else 1)
