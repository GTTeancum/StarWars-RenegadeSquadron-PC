from pathlib import Path
p=Path('/mnt/data/renegade/intake/sources/PSPRecomp/profiles/renegade/host/psp_services.cpp');t=p.read_text()
t=t.replace('    IoDeferred,\n    Completed,','    IoDeferred,\n    WaitingEnd,\n    Completed,',1)
t=t.replace('struct ThreadRecord {','''struct EndWaitState {
    std::int32_t target{};
    std::uint32_t timeout_pointer{};
    std::uint64_t deadline{UINT64_MAX};
    psprecomp::Runtime* runtime{};
    psprecomp::AllegrexContext original{};
    bool callbacks{};
};
struct ThreadRecord {''',1)
t=t.replace('    std::uint64_t delay_sequence{};\n};','    std::uint64_t delay_sequence{};\n    std::vector<EndWaitState> end_waits;\n};',1)
# Helpers precede promote_expired_delays and can see the complete global scheduler state.
anchor='void promote_expired_delays() {'
helpers=r'''
auto pending_user_callback(std::int32_t owner) {
    auto best=callback_table.callbacks.end();
    for(auto it=callback_table.callbacks.begin();it!=callback_table.callbacks.end();++it)
        if(it->second.owner_uid==owner && it->second.notify_count && it->second.function &&
           (best==callback_table.callbacks.end() || it->first<best->first))best=it;
    return best;
}
bool dispatch_user_callback(psprecomp::AllegrexContext& ctx,const psprecomp::AllegrexContext& resume) {
    auto found=pending_user_callback(thread_table.current_uid);
    if(found==callback_table.callbacks.end())return false;
    auto& frames=async_return_frames[thread_table.current_uid];
    if(!frames.empty())return false; // Pending notification must not be discarded while nested.
    auto& cb=found->second;auto count=cb.notify_count,argument=cb.notify_argument;cb.notify_count=0;
    frames.push_back(AsyncReturnFrame{AsyncReturnKind::UserCallback,resume,0u,0,0,0,found->first});
    ctx.set_gpr(4,count);ctx.set_gpr(5,argument);ctx.set_gpr(6,cb.common);ctx.set_gpr(31,4);ctx.pc=cb.function;
    return true;
}
void finish_end_wait(ThreadRecord& thread) {
    if(thread.end_waits.empty())return;
    auto w=thread.end_waits.back();thread.end_waits.pop_back();
    if(w.timeout_pointer){auto left=w.deadline>virtual_time_us?w.deadline-virtual_time_us:0;
        w.runtime->memory().store32(w.timeout_pointer,static_cast<std::uint32_t>(std::min<std::uint64_t>(left,UINT32_MAX)));}
}
void promote_end_waiters() {
    struct Ready {std::int32_t target,uid;psprecomp::AllegrexContext context;std::uint64_t sequence;bool expired;};
    std::vector<Ready> ready;
    for(auto& [target,waiters]:thread_table.thread_end_waiters)for(auto& waiter:waiters){
        auto it=thread_table.threads.find(waiter.uid);if(it==thread_table.threads.end() || it->second.end_waits.empty())continue;
        auto& w=it->second.end_waits.back();
        const bool expired=w.deadline!=UINT64_MAX && virtual_time_us>=w.deadline;
        const auto frame=async_return_frames.find(waiter.uid);
        const bool callback=w.callbacks && pending_user_callback(waiter.uid)!=callback_table.callbacks.end() && (frame==async_return_frames.end() || frame->second.empty());
        if(expired || callback)ready.push_back({target,waiter.uid,expired?waiter.context:w.original,waiter.ready_sequence,expired});
    }
    std::sort(ready.begin(),ready.end(),[](const Ready& a,const Ready& b){return a.sequence!=b.sequence?a.sequence<b.sequence:a.uid<b.uid;});
    for(auto& item:ready){auto it=thread_table.threads.find(item.uid);if(it==thread_table.threads.end())continue;
        auto& waiters=thread_table.thread_end_waiters[item.target];std::erase_if(waiters,[&](const auto& w){return w.uid==item.uid;});
        if(item.expired){item.context.set_gpr(2,0x800201a8u);finish_end_wait(it->second);}
        enqueue_continuation(item.uid,item.context);
    }
    std::erase_if(thread_table.thread_end_waiters,[](const auto& item){return item.second.empty();});
}
'''
assert anchor in t;t=t.replace(anchor,helpers+'\n'+anchor+'\n    promote_end_waiters();',1)
t=t.replace('if (thread.state == ThreadState::Delayed)\n                earliest = std::min(earliest, thread.delay_until_us);','''if (thread.state == ThreadState::Delayed)
                earliest = std::min(earliest, thread.delay_until_us);
            if (thread.state == ThreadState::WaitingEnd && !thread.end_waits.empty())
                earliest = std::min(earliest, thread.end_waits.back().deadline);''',1)
t=t.replace('void remove_thread_from_wait_queues(std::int32_t uid) {','''void remove_thread_from_wait_queues(std::int32_t uid) {
    if(auto thread=thread_table.threads.find(uid);thread!=thread_table.threads.end())thread->second.end_waits.clear();''',1)
t=t.replace('''    for (auto &waiter : found->second) {
        waiter.context.set_gpr(2, result);
        enqueue_continuation(waiter.uid, waiter.context);
    }
    thread_table.thread_end_waiters.erase(found);''','''    for (auto &waiter : found->second) {
        waiter.context.set_gpr(2, result);
        if(auto thread=thread_table.threads.find(waiter.uid);thread!=thread_table.threads.end())finish_end_wait(thread->second);
        enqueue_continuation(waiter.uid, waiter.context);
    }
    thread_table.thread_end_waiters.erase(found);''',1)
a=t.index('    runtime.register_hle("ThreadManForUser", 0x278C0DF5u,');b=t.index('    auto delay_thread =',a)
t=t[:a]+r'''    const auto wait_thread_end = [](bool callbacks) {
      return [callbacks](psprecomp::Runtime& rt,psprecomp::AllegrexContext& ctx) {
        const auto uid=static_cast<std::int32_t>(ctx.gpr[4]);auto target=thread_table.threads.find(uid);auto current=thread_table.threads.find(thread_table.current_uid);
        if(uid==0 || uid==thread_table.current_uid){ctx.set_gpr(2,0x80020197u);return;}
        if(target==thread_table.threads.end() || current==thread_table.threads.end()){ctx.set_gpr(2,0x80020198u);return;}
        const auto timeout=ctx.gpr[5];if(timeout && !rt.memory().contains(timeout,4)){ctx.set_gpr(2,0x800200d3u);return;}
        auto& stack=current->second.end_waits;
        if(stack.empty() || stack.back().original.pc!=ctx.pc || stack.back().target!=uid){
            const auto deadline=timeout?virtual_time_us+rt.memory().load32(timeout):UINT64_MAX;
            stack.push_back(EndWaitState{uid,timeout,deadline,&rt,ctx,callbacks});
        }
        if(target->second.state==ThreadState::Completed || target->second.state==ThreadState::Created){finish_end_wait(current->second);ctx.set_gpr(2,0);return;}
        if(stack.back().deadline!=UINT64_MAX && virtual_time_us>=stack.back().deadline){finish_end_wait(current->second);ctx.set_gpr(2,0x800201a8u);return;}
        if(callbacks && dispatch_user_callback(ctx,stack.back().original))return;
        auto continuation=make_wait_context(ctx);
        thread_table.thread_end_waiters[uid].push_back({thread_table.current_uid,continuation,thread_table.next_delay_sequence++});
        current->second.state=ThreadState::WaitingEnd;current->second.suspended_context=continuation;
        if(std::getenv("PSPRECOMP_THREAD_DIAG"))std::cerr<<"[thread] wait-end owner="<<thread_table.current_uid<<" target="<<uid<<" callbacks="<<callbacks<<"\n";
        if(!activate_next_thread(ctx,"thread-end-wait"))rt.stop("PSP scheduler has no runnable or timed thread while waiting for thread "+std::to_string(uid));
      };
    };
    runtime.register_hle("ThreadManForUser",0x278C0DF5u,wait_thread_end(false));
    runtime.register_hle("ThreadManForUser",0x840E8133u,wait_thread_end(true));
    runtime.register_hle("ThreadManForUser",0x3B183E26u,
      [](psprecomp::Runtime&,psprecomp::AllegrexContext& ctx){auto it=thread_table.threads.find(static_cast<std::int32_t>(ctx.gpr[4]));
        ctx.set_gpr(2,it==thread_table.threads.end()?0x80020198u:(it->second.state==ThreadState::Completed || it->second.state==ThreadState::Created)?it->second.exit_status:0x800201a4u);
      });

'''+t[b:]
a=t.index('    runtime.register_hle("ThreadManForUser", 0x349D6D6Cu,');b=t.index('    runtime.register_hle("ThreadManForUser", 0xD6DA4BA1u,',a)
t=t[:a]+r'''    runtime.register_hle("ThreadManForUser",0x349D6D6Cu,
      [](psprecomp::Runtime&,psprecomp::AllegrexContext& ctx){virtual_time_us+=25;promote_expired_delays();
        auto resume=make_wait_context(ctx);resume.set_gpr(2,1);
        if(!dispatch_user_callback(ctx,resume)){set_success(ctx);(void)preempt_if_higher_priority(ctx,"check-callback");}
      });
    runtime.register_hle("ThreadManForUser",0xC11BA8C4u,
      [](psprecomp::Runtime&,psprecomp::AllegrexContext& ctx){auto found=callback_table.callbacks.find(static_cast<std::int32_t>(ctx.gpr[4]));
        if(found==callback_table.callbacks.end()){ctx.set_gpr(2,0x800201a1u);return;}
        ++found->second.notify_count;found->second.notify_argument=ctx.gpr[5];set_success(ctx);promote_end_waiters();(void)preempt_if_higher_priority(ctx,"callback-notify");
      });

'''+t[b:]
p.write_text(t)
