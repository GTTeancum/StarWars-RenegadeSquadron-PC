#include "../host/override_commands.hpp"
#include "psprecomp/runtime.hpp"
#include <iostream>
#include <stdexcept>
using namespace renegade::overrides;
int main(){
    unsigned checks=0;auto check=[&](bool value,const char* why){++checks;if(!value)throw std::runtime_error(why);};
    try {
        CommandPoseStore store;PoseIdentity id{{1,2,3,4,5,6},7,8};
        auto pose=std::make_shared<PoseSnapshot>();pose->identity=id;pose->serial=42;pose->bones.resize(2);
        constexpr unsigned word=0x04040003,va=0x08801000,ia=0x08802000,pc=0x08803000;
        auto begin=[&](){return store.begin(id,2);};
        auto first=begin();check(store.record(first,0,pc,word,va,ia),"Tag before pose completion");
        check(store.complete(first,pose),"Publish complete pose");
        auto second=begin();check(store.complete(second,pose)&&store.record(second,0,pc+4,word,va,ia),"Same matrices at a different command address");
        auto a=store.consume(pc,word,va,ia),b=store.consume(pc+4,word,va,ia);
        check(a.pose==pose&&a.batch==first&&b.batch==second,"Command address distinguishes identical poses");
        check(!store.consume(pc,word,va,ia).pose,"Consumed command cannot replay stale pose");
        auto partial=begin();store.record(partial,0,pc,word,va,ia);
        check(!store.consume(pc,word,va,ia).pose&&!store.complete(partial,pose),"Early execution rejects entire incomplete batch");
        auto wrong=begin();store.complete(wrong,pose);store.record(wrong,0,pc,word,va,ia);store.record(wrong,1,pc+4,word,va,ia);
        check(!store.consume(pc,word,va+32,ia).pose&&!store.consume(pc+4,word,va,ia).pose,"Changed addresses reject remaining batch");
        auto old=begin();store.complete(old,pose);store.record(old,0,pc,word,va,ia);store.record(old,1,pc+4,word,va,ia);
        auto reused=begin();store.complete(reused,pose);store.record(reused,0,pc,word,va,ia);
        check(!store.consume(pc+4,word,va,ia).pose&&store.consume(pc,word,va,ia).batch==reused,"Reused command buffer invalidates previous owner");
        auto changed=begin();store.complete(changed,pose);store.record(changed,0,pc,word,va,ia);
        check(!store.consume(pc,word+1,va,ia).pose,"Changed primitive word rejected");
        auto mismatch=std::make_shared<PoseSnapshot>(*pose);mismatch->identity.context++;
        check(!store.complete(begin(),mismatch),"Wrong pose identity rejected");
        mismatch->identity=id;mismatch->bones.resize(1);
        check(!store.complete(begin(),mismatch),"Incomplete bone vector rejected");
        auto expired=begin();store.complete(expired,pose);store.record(expired,0,pc,word,va,ia);
        for(unsigned i=0;i<CommandPoseStore::capacity;++i)begin();
        check(!store.consume(pc,word,va,ia).pose&&a.pose->serial==42,"Eviction removes association and preserves external immutable pose");
        check(!store.begin(id,0)&&!store.begin(id,257),"Bone count budget");
        check(!store.record(begin(),2,pc,word,va,ia),"Out-of-range slot rejected");
        check(!store.record(begin(),0,pc+1,word,va,ia),"Unaligned command rejected");
        auto missing=begin();store.expect(missing,0,true);store.expect(missing,1,true);
        store.record(missing,0,pc,word,va,ia);store.complete(missing,pose);
        check(!store.consume(pc,word,va,ia).pose&&!store.record(missing,1,pc+4,word,va,ia),
              "Complete matrices without every populated command retain entire original batch");
        auto drawn=begin();store.complete(drawn,pose);store.record(drawn,0,pc,word,va,ia);store.record(drawn,1,pc+4,word,va,ia);
        auto decision=store.consume(pc,word,va,ia);decision.draw->status=CommandDrawStatus::Replaced;store.reject(drawn);
        check(store.consume(pc+4,word,va,ia).draw==decision.draw,"Already replaced batch keeps suppressing its remaining valid tags");
        auto retired=begin();store.complete(retired,pose);store.record(retired,0,pc,word,va,ia);store.record(retired,1,pc+4,word,va,ia);
        auto rendered=store.consume(pc,word,va,ia);rendered.draw->status=CommandDrawStatus::Replaced;
        for(unsigned i=0;i<CommandPoseStore::capacity;++i)begin();
        auto tail=store.consume(pc+4,word,va,ia);
        check(!tail.pose&&tail.draw==rendered.draw&&tail.resource==id.resource,
              "Evicted rendered batch preserves bounded suppression metadata without retaining pose");
        check(rendered.pose->serial==42,"External pose survives suppression-only retirement");
        CommandPoseStore pressure;auto crowded=pressure.begin(id,2);pressure.complete(crowded,pose);
        bool filled=true;for(unsigned i=0;i<CommandPoseStore::command_capacity;++i)
            filled&=pressure.record(crowded,0,pc+i*4,word,va,ia);
        check(filled&&!pressure.record(crowded,1,pc+CommandPoseStore::command_capacity*4,word,va,ia)&&
              !pressure.consume(pc,word,va,ia).pose,"Command budget rejects unrendered batch instead of mixing partial replacement");
        psprecomp::Runtime rt;auto& memory=rt.memory();psprecomp::AllegrexContext c{};
        memory.aot_store32(0x08c38270,0);
        c.gpr[31]=0x08905FFC;c.gpr[2]=pc-12;c.gpr[3]=word;c.gpr[7]=ia;
        c.gpr[11]=0x10080000;
        // 0x08801000 = base high 0x08 + low 0x801000.
        c.gpr[12]=0x01801000;
        command_pose_store.clear();reset_command_submission();
        auto single=std::make_shared<PoseSnapshot>(*pose);single->bones.resize(1);
        command_submission(id,1,0,va,ia,word&0xffffff,single);
        emitted_command(rt,c);
        check(command_pose_store.consume(pc,word,va,ia).pose==single,"Original emitter register decoding associates exact command");
        c.gpr[31]=0x08906058;c.gpr[2]+=24;emitted_command(rt,c);
        check(command_pose_store.consume(pc+24,word,va,ia).pose==single,"Second material pass retains the same pose association");
        c.gpr[2]=pc-12;
        reset_command_submission();command_submission(id,1,0,va,ia,word&0xffffff,single);
        c.gpr[31]=0;emitted_command(rt,c);
        check(!command_pose_store.consume(pc,word,va,ia).pose,"Unrelated caller cannot tag a command");
        c.gpr[31]=0x08906058;c.gpr[7]=ia+2;emitted_command(rt,c);
        check(!command_pose_store.consume(pc,word,va,ia).pose,"Emitter input mismatch rejects batch");
        std::cout<<checks<<" command pose checks passed\n";return 0;
    }catch(const std::exception& e){std::cerr<<"After "<<checks<<" checks: "<<e.what()<<'\n';return 1;}
}
