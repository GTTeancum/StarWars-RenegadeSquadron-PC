#include "override_commands.hpp"
#include "override_resource_registry.hpp"
#include "psprecomp/runtime.hpp"
#include <cstdlib>
#include <fstream>

namespace renegade::overrides {
namespace {
struct Pending {
    PoseIdentity id;unsigned count{},next{},slot{};std::uint64_t batch{},emission{};
    std::uint32_t va{},ia{},primitive{};
};
thread_local Pending pending;
void debug_event(const char* event,std::uint64_t batch,unsigned slot,std::uint32_t pc,
                 std::uint32_t word,std::uint32_t va,std::uint32_t ia){
    static const char* output=std::getenv("RENEGADE_TRACE_COMMAND_POSES");if(!output||!*output)return;
    static std::map<std::string,unsigned> counts;if(counts[event]++>=32)return;
    static std::ofstream log(std::string(output)+".debug.jsonl",std::ios::trunc);if(!log)return;
    log<<"{\"event\":\""<<event<<"\",\"batch\":"<<batch<<",\"slot\":"<<slot<<",\"pc\":"<<pc
       <<",\"word\":"<<word<<",\"va\":"<<va<<",\"ia\":"<<ia<<"}\n";log.flush();
}
}
void reset_command_submission(){pending.emission=0;}
void command_submission(const PoseIdentity& id,unsigned count,unsigned slot,std::uint32_t va,
                        std::uint32_t ia,std::uint32_t primitive,std::shared_ptr<const PoseSnapshot> pose){
    if(slot==0){
        if(pending.batch&&pending.next!=pending.count)command_pose_store.reject(pending.batch);
        pending={};pending.id=id;pending.count=count;pending.batch=command_pose_store.begin(id,count);
    }
    if(!pending.batch||pending.id!=id||pending.count!=count||pending.next!=slot){
        command_pose_store.reject(pending.batch);pending={};return;
    }
    ++pending.next;pending.slot=slot;pending.va=va;pending.ia=ia;pending.primitive=primitive;
    command_pose_store.expect(pending.batch,slot,primitive!=0);
    pending.emission=primitive?pending.batch:0;
    debug_event("submission",pending.batch,slot,0,primitive,va,ia);
    if(slot+1==count){auto ok=command_pose_store.complete(pending.batch,std::move(pose));
        debug_event(ok?"complete":"complete_rejected",pending.batch,slot,0,0,0,0);}
}
void emitted_command(psprecomp::Runtime& rt,const psprecomp::AllegrexContext& c) noexcept {
    if(!pending.emission)return;
    try {
        debug_event("emitter",pending.emission,pending.slot,c.gpr[2]+12,c.gpr[31],c.gpr[12],c.gpr[7]);
        if(c.gpr[31]!=0x08905FFC&&c.gpr[31]!=0x08906058)return;
        // The material path may emit a second pass for this same part. Keep its
        // association until the next original submission resets the emission.
        const auto token=pending.emission;
        const auto& m=rt.memory();
        // Original emitter encodes VA relative to the current GU offset.
        constexpr std::uint32_t origin=0x08c38270;
        if(!m.contains(origin,4)||!m.contains(c.gpr[2],16)){command_pose_store.reject(token);return;}
        auto va=psprecomp::GuestMemory::canonical((((c.gpr[11]&0x1f0000)<<8)|(c.gpr[12]&0xffffff))+m.aot_load32(origin));
        auto ia=psprecomp::GuestMemory::canonical(c.gpr[7]);
        auto pc=psprecomp::GuestMemory::canonical(c.gpr[2]+12);
        if(va!=pending.va||ia!=pending.ia||c.gpr[3]!=(0x04000000|pending.primitive)){
            debug_event("emitter_mismatch",token,pending.slot,pc,c.gpr[3],va,ia);
            command_pose_store.reject(token);return;
        }
        const bool ok=command_pose_store.record(token,pending.slot,pc,c.gpr[3],va,ia);
        debug_event(ok?"recorded":"record_rejected",token,pending.slot,pc,c.gpr[3],va,ia);
    }catch(...){command_pose_store.reject(pending.batch);}
}
CommandPose trace_command_pose(const psprecomp::GuestMemory& memory,std::uint32_t pc,std::uint32_t va,
                        std::uint32_t ia,std::uint32_t primitive) noexcept {
    static const char* root=std::getenv("RENEGADE_OVERRIDE_ROOT");
    if(!root||!*root||!pc)return {};
    try {
        pc=psprecomp::GuestMemory::canonical(pc);va=psprecomp::GuestMemory::canonical(va);ia=psprecomp::GuestMemory::canonical(ia);
        auto result=command_pose_store.consume(pc,0x04000000|primitive,va,ia);
        if(!result.pose&&(!result.draw||result.draw->status!=CommandDrawStatus::Replaced)){
            static const char* debug=std::getenv("RENEGADE_TRACE_COMMAND_POSES");
            if(debug&&*debug){auto part=render_resources::resolve_part(memory,va,ia,primitive);
                if(part.resource&&part.resource->name=="battle_droid")debug_event("consume_miss",0,part.slot,pc,primitive,va,ia);}
            return {};
        }
        const auto& r=result.resource;
        auto live=render_resources::find_record(memory,r[0]);
        if(!live||std::array<std::uint32_t,6>{live->record,live->key,live->vertices,live->indices,live->vertex_count,live->index_count}!=r){
            command_pose_store.reject(result.batch);return {};
        }
        if(!result.pose)return result; // Valid suppression-only tag after pose eviction.
        static const char* output=std::getenv("RENEGADE_TRACE_COMMAND_POSES");
        if(!output||!*output)return result;
        static unsigned samples=0;if(samples>=512)return result;
        static std::ofstream log(output,std::ios::trunc);if(!log)return result;
        log<<"{\"sample\":"<<++samples<<",\"pc\":"<<pc<<",\"batch\":"<<result.batch
           <<",\"pose_serial\":"<<result.pose->serial<<",\"slot\":"<<result.slot
           <<",\"vertex_address\":"<<va<<",\"index_address\":"<<ia<<",\"primitive\":"<<primitive<<"}\n";
        log.flush();
        return result;
    }catch(...){}
    return {};
}
}
