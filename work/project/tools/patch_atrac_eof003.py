from pathlib import Path
S=Path('/mnt/data/renegade/intake/sources/PSPRecomp');P=S/'profiles/renegade';f=P/'host/psp_services.cpp';t=f.read_text()
a='''                if (remain_addr != 0u) rt.memory().store32(remain_addr, 0u);
                set_success(ctx);
                return;
            }
            const std::uint32_t requested_samples'''
b='''                if (remain_addr != 0u) rt.memory().store32(remain_addr,
                    state->next_file_offset >= state->header.file_size ? 0xFFFFFFFFu : 0u);
                // PSP_ATRAC_ERROR_ALLDATA_WAS_DECODED (PSPSDK pspatrac3.h).
                // Returning success with zero samples makes a client that fills
                // a fixed-size output block spin forever after the last frame.
                ctx.set_gpr(2, 0x80630024u);
                return;
            }
            const std::uint32_t requested_samples'''
assert t.count(a)==1;t=t.replace(a,b)
a='''            const std::uint32_t remaining_frames = state->header.block_align == 0u ? 0u :
                state->buffered_encoded_bytes / state->header.block_align;'''
b='''            const std::uint32_t remaining_frames = state->next_file_offset >= state->header.file_size
                ? 0xFFFFFFFFu : (state->header.block_align == 0u ? 0u :
                state->buffered_encoded_bytes / state->header.block_align);'''
assert t.count(a)==1;t=t.replace(a,b)
a='''            // hardware pacing at the end of the pipeline; ATRAC decode itself
            // must return as soon as its PCM is ready.
            set_success(ctx);
        });'''
b='''            // hardware pacing at the end of the pipeline; ATRAC decode itself
            // must return as soon as its PCM is ready. A decoder which has no
            // PCM left must signal end, not a successful zero-length frame.
            if (samples == 0u) ctx.set_gpr(2, 0x80630024u);
            else set_success(ctx);
        });'''
assert t.count(a)==1;t=t.replace(a,b)
end='} // namespace vcs\n';assert t.endswith(end)
t=t[:-len(end)]+r'''
// Separate executable only: tests the real registered HLE at the end of data.
bool run_renegade_atrac_tests(std::string& error) {
 unsigned checks=0;
 try {
   auto p=std::make_unique<psprecomp::Runtime>();auto& r=*p;install_profile(r,0x08c40000u);
   auto& c=r.cpu();auto& m=r.memory();
   auto check=[&](bool value,const char* msg){++checks;if(!value)throw psprecomp::Error(msg);};
   constexpr unsigned out=0x08820000u,n=0x08821000u,endflag=n+4,remain=n+8;
   auto& s=atrac_contexts[0];s.allocated=true;s.header.atrac3plus=false;
   s.header.total_samples=1024;s.sample_position=1024;s.header.file_size=4096;s.next_file_offset=4096;
   s.source_path="synthetic-drained-stream";s.loop_num=0;s.header.loop_start=-1;
   auto decode=[&](unsigned id,unsigned buf=out,unsigned sn=n,unsigned fn=endflag,unsigned rn=remain){
     c={};c.pc=0x08801000;c.gpr[31]=0x08801008;c.gpr[4]=id;c.gpr[5]=buf;c.gpr[6]=sn;c.gpr[7]=fn;c.gpr[8]=rn;
     r.invoke_import("sceAtrac3plus",0x6A8C3CD5,c);check(!r.stopped(),"ATRAC import unexpectedly stopped");return c.gpr[2];
   };
   for(unsigned i=0;i<8;++i){m.store32(n,0x55555555);m.store32(endflag,0x55555555);m.store32(remain,0x55555555);m.store32(out,0xDEADBEEF);
     check(decode(0)==0x80630024,"drained stream returned successful empty frame");
     check(m.load32(n)==0 && m.load32(endflag)==1,"end outputs incorrect");
     check(m.load32(remain)==0xFFFFFFFF,"fully buffered remaining flag incorrect");
     check(m.load32(out)==0xDEADBEEF,"drained decoder touched PCM output");
   }
   s.next_file_offset=2048;check(decode(0)==0x80630024 && m.load32(remain)==0,"partial-buffer EOF status");
   check(decode(99)==0x80630005,"invalid ATRAC id");
   check(decode(0,out,0x09FFFFFE)==0x800200D3,"output bounds rejected");
   check(decode(0,0,0,0,0)==0x80630024,"optional null result pointers");
   s.allocated=false;std::cerr<<"PASS "<<checks<<" ATRAC terminal/bounds checks\n";error.clear();return true;
 }catch(const std::exception& e){error="after "+std::to_string(checks)+" checks: "+e.what();return false;}
}
''' +end
f.write_text(t)
(P/'tests/atrac003.cpp').write_text('''#include <iostream>\n#include <string>\nnamespace vcs {bool run_renegade_atrac_tests(std::string&);}\nint main(){std::string error;if(!vcs::run_renegade_atrac_tests(error)){std::cerr<<"FAIL "<<error<<"\\n";return 1;}return 0;}\n''')
f=P/'CMakeLists.txt';t=f.read_text();t=t.replace('''if(DEFINED ENV{RENEGADE_DISC_ROOT})
 add_test(NAME renegade_psmf_asset_tests COMMAND renegade_platform_tests "$ENV{RENEGADE_DISC_ROOT}")
endif()''','''set(RENEGADE_DISC_ROOT "$ENV{RENEGADE_DISC_ROOT}" CACHE PATH "Optional user-owned extracted disc for asset-dependent tests")
if(RENEGADE_DISC_ROOT)
 add_test(NAME renegade_psmf_asset_tests COMMAND renegade_platform_tests "${RENEGADE_DISC_ROOT}")
endif()''')
t+='''\nadd_executable(renegade_atrac_tests tests/atrac003.cpp)\ntarget_link_libraries(renegade_atrac_tests PRIVATE renegade_services)\nadd_test(NAME renegade_atrac_tests COMMAND renegade_atrac_tests)\n''';f.write_text(t)
