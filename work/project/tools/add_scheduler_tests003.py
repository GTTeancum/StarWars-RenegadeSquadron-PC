from pathlib import Path
s=Path('/mnt/data/renegade/intake/sources/PSPRecomp/profiles/renegade');p=s/'host/psp_services.cpp';t=p.read_text()
t=t.replace('    case ThreadState::IoDeferred: return "IoDeferred";','    case ThreadState::IoDeferred: return "IoDeferred";\n    case ThreadState::WaitingEnd: return "WaitingEnd";')
assert t.endswith('} // namespace vcs\n')
t=t[:-len('} // namespace vcs\n')]+r'''
// Test-only entry called by a separate executable, never by the game host.
bool run_renegade_scheduler_tests(std::string& error) {
 unsigned checks=0;
 try {
    auto heap=std::make_unique<psprecomp::Runtime>();auto& r=*heap;auto& c=r.cpu();
    const auto check=[&](bool value,const char* message){++checks;if(!value)throw psprecomp::Error(message);};
    constexpr std::uint32_t ptr=0x08850000u,ret=0x08800100u,import_pc=0x08ad2c00u;
    auto setup=[&](bool ready=true){install_profile(r,0x08c40000u);thread_table.threads.clear();thread_table.continuations.clear();thread_table.current_uid=1;
      ThreadRecord parent;parent.name="synthetic waiter";parent.state=ThreadState::Running;parent.priority=16;thread_table.threads[1]=parent;
      ThreadRecord child;child.name="synthetic worker";child.state=ready?ThreadState::Ready:ThreadState::Sleeping;child.priority=32;thread_table.threads[2]=child;
      c={};c.pc=import_pc;c.gpr[29]=0x09ff0000;c.gpr[31]=ret;psprecomp::set_runtime_thread_identity(1,"synthetic waiter");
      if(ready){auto worker=c;worker.pc=0x08800200;enqueue_continuation(2,worker);}
    };
    auto invoke=[&](unsigned nid,unsigned a=0,unsigned b=0){c.pc=import_pc;c.gpr[31]=ret;c.gpr[4]=a;c.gpr[5]=b;r.invoke_import("ThreadManForUser",nid,c);check(!r.stopped(),"scheduler test unexpectedly stopped");};
    setup();r.memory().store32(ptr,1000);invoke(0x840e8133,2,ptr);
    check(thread_table.current_uid==2 && thread_table.threads.at(1).state==ThreadState::WaitingEnd,"CB wait failed to block until actual worker exit");
    invoke(0xd59ead2f,1);check(thread_table.threads.at(1).state==ThreadState::WaitingEnd,"WakeupThread incorrectly completed thread-end wait");
    virtual_time_us+=300;invoke(0xaa73c935,0x12345678);check(thread_table.current_uid==1 && c.pc==ret && c.gpr[2]==0,"exit did not wake and return waiter");
    check(r.memory().load32(ptr)<=700 && r.memory().load32(ptr)>0,"remaining timeout not written");check(thread_table.threads.at(1).end_waits.empty(),"completed wait leaked state");
    invoke(0x3b183e26,2);check(c.gpr[2]==0x12345678,"real exit status was lost");
    invoke(0x840e8133,2,0);check(c.gpr[2]==0,"waiting already-completed thread failed");
    setup(false);r.memory().store32(ptr,125);invoke(0x840e8133,2,ptr);
    check(thread_table.current_uid==1 && c.gpr[2]==0x800201a8 && r.memory().load32(ptr)==0,"idle scheduler failed to honor wait timeout");check(thread_table.thread_end_waiters.empty(),"timed-out waiter was retained");
    setup();invoke(0x278c0df5,1,0);check(c.gpr[2]==0x80020197,"self wait accepted");invoke(0x278c0df5,99,0);check(c.gpr[2]==0x80020198,"unknown wait accepted");invoke(0x278c0df5,2,0x09fffffe);check(c.gpr[2]==0x800200d3,"invalid timeout pointer accepted");
    setup();callback_table.callbacks[0x201]=CallbackRecord{"synthetic callback",0x08840000,0x55,1,1,0x66};r.memory().store32(ptr,1000);invoke(0x840e8133,2,ptr);
    check(thread_table.current_uid==1 && c.pc==0x08840000 && c.gpr[4]==1 && c.gpr[5]==0x66 && c.gpr[6]==0x55,"CB wait did not dispatch notification with proper arguments");
    check(async_return_frames.at(1).back().resume.pc==import_pc,"CB wait falsely completed after callback instead of re-entering wait");
    virtual_time_us=100;vcs_interrupt_return(r,c);check(c.pc==import_pc && c.gpr[4]==2 && c.gpr[5]==ptr,"callback failed to restore wait arguments");
    r.invoke_import("ThreadManForUser",0x840e8133,c);check(thread_table.current_uid==2,"wait did not resume blocking after callback");
    virtual_time_us=200;invoke(0xaa73c935,7);check(c.gpr[2]==0 && r.memory().load32(ptr)==800,"callback reset wait deadline or blocked successful completion");
    setup();r.memory().store32(ptr,1000);invoke(0x840e8133,2,ptr);callback_table.callbacks[0x202]=CallbackRecord{"later callback",0x08840004,0x77,1,0,0};
    invoke(0xc11ba8c4,0x202,0x88);check(thread_table.current_uid==1 && c.pc==import_pc,"NotifyCallback failed to wake a callback-enabled wait");
    r.invoke_import("ThreadManForUser",0x840e8133,c);check(c.pc==0x08840004 && c.gpr[5]==0x88,"notified callback was not executed at CB checkpoint");
    setup();callback_table.callbacks[0x203]=CallbackRecord{"nested pending",0x08840008,0,1,1,0};async_return_frames[1].push_back(AsyncReturnFrame{AsyncReturnKind::UserCallback,c});invoke(0x349d6d6c);
    check(callback_table.callbacks[0x203].notify_count==1,"nested callback check discarded pending notification");
    async_return_frames.clear();invoke(0x349d6d6c);check(c.pc==0x08840008 && callback_table.callbacks[0x203].notify_count==0,"deferred notification was not delivered later");
    std::cerr<<"PASS "<<checks<<" scheduler/wait/callback checks\n";error.clear();return true;
 } catch(const std::exception& e){error="after "+std::to_string(checks)+" checks: "+e.what();return false;}
}
} // namespace vcs
''';p.write_text(t)
(s/'tests/scheduler003.cpp').write_text('''#include <iostream>
#include <string>
namespace vcs {bool run_renegade_scheduler_tests(std::string&);}
int main(){std::string error;if(!vcs::run_renegade_scheduler_tests(error)){std::cerr<<"FAIL "<<error<<"\\n";return 1;}return 0;}
''')
p=s/'CMakeLists.txt';p.write_text(p.read_text()+'''\nadd_executable(renegade_scheduler_tests tests/scheduler003.cpp)
target_link_libraries(renegade_scheduler_tests PRIVATE renegade_services)
add_test(NAME renegade_scheduler_tests COMMAND renegade_scheduler_tests)
''')
