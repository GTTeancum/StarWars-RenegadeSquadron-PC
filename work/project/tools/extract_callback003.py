#!/usr/bin/env python3
"""Remove unrelated generated import wrappers, preserving the original callback body."""
from pathlib import Path
import re,hashlib,json
R=Path('/mnt/data/renegade');S=R/'intake/sources/PSPRecomp';p=R/'tools/callback003.full.cpp';text=p.read_text();body=text[:text.index('static void import_0')]
regs=re.findall(r'    runtime.register_function\((0x[0-9A-Fa-f]+)u, &renegade_callback_08896118, "([^"]+)"\);',text)
assert len(regs)==8
body+='void register_supplemental_functions(Runtime &runtime) {\n'
for addr,name in regs:body+=f'    if (!runtime.has_function({addr}u)) runtime.register_function({addr}u, &renegade_callback_08896118, "{name}");\n'
body+='}\n} // namespace psprecomp\n'
out=S/'profiles/renegade/supplemental/callback_08896118.cpp';out.parent.mkdir(exist_ok=True);out.write_text(body)
(R/'analysis/callback003.json').write_text(json.dumps({'boot_sha256':'f4c7a9ef93475fc8017f649346ef79b599649dc47462ec419e9fd373146f8c68','generator_sha256':hashlib.sha256((R/'intake/out/framework/psp_recomp').read_bytes()).hexdigest(),'address':'0x08896118','byte_length':40,'entry_labels':[a for a,n in regs],'source_sha256':hashlib.sha256(body.encode()).hexdigest(),'transform':'Only remove unrelated imports/registration; retain original generated function body and add missing-only registration'},indent=2))
