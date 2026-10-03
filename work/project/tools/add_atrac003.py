from pathlib import Path
p=Path('/mnt/data/renegade/intake/sources/PSPRecomp/profiles/renegade/host/psp_services.cpp');t=p.read_text()
a=t.index('    runtime.register_hle("sceAtrac3plus", 0x0FAE370Eu,')
b=t.index('    runtime.register_hle("sceAtrac3plus", 0x61EB33F5u,',a)
chunk=t[a:b]
chunk=chunk.replace('    runtime.register_hle("sceAtrac3plus", 0x0FAE370Eu,\n        []','    const auto set_atrac_buffer = []',1)
assert chunk.endswith('        });\n\n')
chunk=chunk[:-len('        });\n\n')]+'''        };
    runtime.register_hle("sceAtrac3plus", 0x0FAE370Eu, set_atrac_buffer);
    runtime.register_hle("sceAtrac3plus", 0x7A20E7AFu,
        [set_atrac_buffer](psprecomp::Runtime &rt, psprecomp::AllegrexContext &ctx) {
            // Full-buffer API: the supplied byte count is also its capacity.
            const auto old_a2 = ctx.gpr[6];
            ctx.set_gpr(6, ctx.gpr[5]);
            set_atrac_buffer(rt, ctx);
            ctx.set_gpr(6, old_a2);
        });

'''
t=t[:a]+chunk+t[b:];p.write_text(t)
