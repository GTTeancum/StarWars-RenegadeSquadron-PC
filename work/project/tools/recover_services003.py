from pathlib import Path
p=Path('/mnt/data/renegade/intake/sources/PSPRecomp/profiles/renegade/host/psp_services.cpp');s=p.read_text()
anchor='''    runtime.register_hle("SysMemUserForUser", 0x237DBD4Fu,'''
addition='''    runtime.register_hle("SysMemUserForUser", 0xF919F628u,
        [](psprecomp::Runtime&, psprecomp::AllegrexContext& ctx) {
            const auto low=(partition_table.next_address+255u)&~255u,high=thread_table.next_stack_top&~255u;
            ctx.set_gpr(2,high>low?high-low:0u);
        });
    runtime.register_hle("UtilsForUser", 0x91E4F6A7u,
        [](psprecomp::Runtime&, psprecomp::AllegrexContext& ctx) {ctx.set_gpr(2,static_cast<std::uint32_t>(system_time_microseconds()));});
    runtime.register_hle("UtilsForUser", 0x27CC57F0u,
        [](psprecomp::Runtime& rt, psprecomp::AllegrexContext& ctx) {
            const auto seconds=static_cast<std::uint32_t>(1720000000ull+system_time_microseconds()/1000000ull);
            if(ctx.gpr[4]){if(!rt.memory().contains(ctx.gpr[4],4)){ctx.set_gpr(2,0xffffffff);return;}rt.memory().store32(ctx.gpr[4],seconds);}
            ctx.set_gpr(2,seconds);
        });
    runtime.register_hle("UtilsForUser", 0x71EC4271u,
        [](psprecomp::Runtime& rt, psprecomp::AllegrexContext& ctx) {
            for(unsigned ptr:{ctx.gpr[4],ctx.gpr[5]})if(ptr && !rt.memory().contains(ptr,8)){ctx.set_gpr(2,0xffffffff);return;}
            const auto us=system_time_microseconds();if(ctx.gpr[4]){rt.memory().store32(ctx.gpr[4],static_cast<std::uint32_t>(1720000000ull+us/1000000));rt.memory().store32(ctx.gpr[4]+4,static_cast<std::uint32_t>(us%1000000));}
            if(ctx.gpr[5]){rt.memory().store32(ctx.gpr[5],0);rt.memory().store32(ctx.gpr[5]+4,0);}ctx.set_gpr(2,0);
        });
    runtime.register_hle("ThreadManForUser", 0x912354A7u,
        [](psprecomp::Runtime&, psprecomp::AllegrexContext& ctx) {
            const auto requested=ctx.gpr[4],priority=requested?requested:thread_priority(thread_table.current_uid);
            if(priority<1 || priority>127){ctx.set_gpr(2,0x80020195u);return;}
            set_success(ctx);
            if(priority==thread_priority(thread_table.current_uid)) {
                const bool equal=std::any_of(thread_table.continuations.begin(),thread_table.continuations.end(),[priority](const ThreadContinuation& c){return thread_priority(c.uid)==priority;});
                if(equal)(void)yield_current_thread(ctx);
            } else {
                auto best=thread_table.continuations.end();for(auto i=thread_table.continuations.begin();i!=thread_table.continuations.end();++i)if(thread_priority(i->uid)==priority && (best==thread_table.continuations.end() || i->ready_sequence<best->ready_sequence))best=i;
                if(best!=thread_table.continuations.end())best->ready_sequence=thread_table.next_ready_sequence++;
                (void)preempt_if_higher_priority(ctx,"rotate-ready");
            }
        });
'''
assert anchor in s;s=s.replace(anchor,addition+anchor)
# Rename neither input logs nor game state. Inherited route-specific deferral must not inspect VCS memory.
begin=s.index('std::uint32_t io_handoff_release_pc(');end=s.index('// A very small host-backed',begin)
s=s[:begin]+'''std::uint32_t io_handoff_release_pc(std::uint32_t handoff_pc) { return handoff_pc; }

'''+s[end:]
begin=s.index('std::uint32_t uncommitted_world_stream_release_pc(');end=s.index('\n}',begin)+2
s=s[:begin]+'''std::uint32_t uncommitted_world_stream_release_pc(psprecomp::Runtime&, std::uint32_t) { return 0u; }'''+s[end:]
p.write_text(s)
