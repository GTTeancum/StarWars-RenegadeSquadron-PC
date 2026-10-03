#!/usr/bin/env python3
from pathlib import Path
import difflib,sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/mnt/data/renegade/intake/sources/PSPRecomp')
p=root/'tools/codegen_main.cpp';s=p.read_text();old=s
s=s.replace('                            continue;\n                        }\n                        // Otherwise run the callee',
'''                            break;  // Finish this block; do not emit the same import JAL forever.
                        }
                        // Otherwise run the callee''')
s=s.replace('''    return "rt.invoke_chained_direct<&" + generated_unit_cpp_name(unit) + ", " +
        std::to_string(unit) + "u>(ctx, &aot_mem)";''','''    return "(ctx.pc = " + psprecomp::hex32(target) + "u, rt.invoke_chained_call(ctx, &aot_mem))";''')
s=s.replace(r'ctx\.vfpu_scalar_bits\(([0-9]+)u\)',r'ctx\.vfpu_scalar_bits\((0|[1-9][0-9]?|1[0-3][0-9]|14[0-3])u\)')
s=s.replace(r'ctx\.set_vfpu_scalar_bits\(([0-9]+)u,',r'ctx\.set_vfpu_scalar_bits\((0|[1-9][0-9]?|1[0-3][0-9]|14[0-3])u,')
if s==old:print('Generator fixes already present (or source differs); inspect revision.');sys.exit(0)
p.write_text(s)
out=Path('/mnt/data/renegade/patches');out.mkdir(parents=True,exist_ok=True)
(out/'codegen_main.cpp.upstream').write_text(old)
(out/'codegen-fixes.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='a/tools/codegen_main.cpp',tofile='b/tools/codegen_main.cpp')))
print('Applied generator fixes')
