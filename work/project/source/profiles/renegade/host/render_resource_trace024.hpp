#pragma once
#include "psprecomp/runtime.hpp"
#include "override_resource_registry.hpp"
#include "override_pose.hpp"
#include "override_skin.hpp"
#include "override_commands.hpp"
#include <algorithm>
#include <cmath>
#include <array>
#include <bit>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <map>
#include <string>

namespace renegade::render_trace024 {
using render_resources::Record;
using render_resources::records;
inline std::string pending_name;
inline const char* path(){static const char* p=std::getenv("RENEGADE_TRACE_RENDER_RESOURCES");return p;}
inline bool enabled(){return path()&&*path();}
inline bool capture_enabled(){static const char* root=std::getenv("RENEGADE_OVERRIDE_ROOT");
    static const char* transforms=std::getenv("RENEGADE_TRACE_MODEL_TRANSFORMS");
    static const char* submissions=std::getenv("RENEGADE_TRACE_MODEL_SUBMISSIONS");
    return enabled()||(root&&*root)||(transforms&&*transforms)||(submissions&&*submissions);}
inline std::ofstream& log(){static std::ofstream f(path(),std::ios::trunc);return f;}
inline void name(psprecomp::Runtime& rt,psprecomp::AllegrexContext& c) noexcept {
    if(!capture_enabled())return;
    try {
        pending_name.clear();
        if(!rt.memory().contains(c.gpr[16],28)||rt.memory().aot_load32(c.gpr[16]+16)!=0)return;
        for(unsigned i=0;i<512;++i){
            if(!rt.memory().contains(c.gpr[2]+i,1)){pending_name.clear();return;}
            auto b=rt.memory().aot_load8(c.gpr[2]+i);if(!b)return;
            if(b<32||b>126){pending_name.clear();return;}pending_name+=char(b);
        }
        pending_name.clear();
    }catch(...){pending_name.clear();}
}
inline void loaded(psprecomp::Runtime& rt,psprecomp::AllegrexContext& c) noexcept {
    if(!capture_enabled()||!c.gpr[20])return;
    try {
        auto& m=rt.memory();auto address=c.gpr[20];
        if(!m.contains(address,28)||!m.contains(c.gpr[29],16))return;
        Record r{pending_name,address,m.aot_load32(c.gpr[29]),m.aot_load32(address+4),
            m.aot_load32(address+8),m.aot_load32(address+16),m.aot_load32(address+20),
            m.aot_load8(address+24)?24u:32u};
        if(!render_resources::register_record(m,r))return;
        if(!enabled())return;
        auto& f=log();if(!f)return;
        f<<"{\"event\":\"load\",\"name\":"<<std::quoted(r.name)<<",\"record\":"<<address
         <<",\"key\":"<<r.key<<",\"vertex_base\":"<<r.vertices<<",\"index_base\":"<<r.indices
         <<",\"vertex_count\":"<<r.vertex_count<<",\"index_count\":"<<r.index_count<<",\"stride\":"<<r.stride;
        auto words=[&](unsigned base,unsigned bytes){f<<'[';if(m.contains(base,bytes))for(unsigned i=0;i<bytes;i+=4){if(i)f<<',';f<<m.aot_load32(base+i);}f<<']';};
        f<<",\"parts\":";auto count=m.aot_load32(address+12);words(m.aot_load32(address),std::min(count,128u)*16);
        f<<",\"vertex_words\":";words(r.vertices,std::min(r.vertex_count,8u)*r.stride);
        f<<"}\n";f.flush();
    }catch(...){}
}
inline void draw(std::uint32_t vertices,std::uint32_t indices,std::uint32_t type,
                 std::uint32_t primitive,std::uint32_t stride) noexcept {
    if(!enabled())return;
    try {
        vertices&=0x1fffffffu;indices&=0x1fffffffu;
        auto it=records.upper_bound(vertices);if(it==records.begin())return;--it;
        auto& r=it->second;
        if(vertices<r.vertices||std::uint64_t(vertices)>=std::uint64_t(r.vertices)+std::uint64_t(r.vertex_count)*r.stride||r.observations>=8)return;
        auto& f=log();if(!f)return;++r.observations;
        f<<"{\"event\":\"draw\",\"name\":"<<std::quoted(r.name)<<",\"record\":"<<r.record
         <<",\"vertex_address\":"<<vertices<<",\"index_address\":"<<indices<<",\"vtype\":"<<type
         <<",\"primitive\":"<<primitive<<",\"decoded_stride\":"<<stride<<",\"index_in_resource\":"
         <<(indices>=r.indices&&std::uint64_t(indices)<std::uint64_t(r.indices)+r.index_count*2ull?"true":"false")<<"}\n";f.flush();
    }catch(...){}
}
// Observe before 08905E90 changes argument registers or rejects empty parts.
// Capture uses owned copies only; diagnostic sampling must not truncate runtime
// animation. No guest writes and no retained guest pointers.
inline void submission(psprecomp::Runtime& rt,const psprecomp::AllegrexContext& c) noexcept {
    static const char* output=std::getenv("RENEGADE_TRACE_MODEL_SUBMISSIONS");
    static const char* root=std::getenv("RENEGADE_OVERRIDE_ROOT");
    if((!output||!*output)&&(!root||!*root))return;
    overrides::reset_command_submission();
    try {
        static unsigned samples=0;
        if(samples>=256&&(!root||!*root))return;
        const auto& m=rt.memory();constexpr unsigned active=0x08bb1e5c,camera=0x08bb1e00;
        if(!m.contains(active,4)||!m.contains(c.gpr[7],64))return;
        auto address=m.aot_load32(active);
        const Record* record=render_resources::find_record(m,address);
        if(!record)return;
        const bool diagnostic=output&&*output&&samples<256&&record->name=="battle_droid";
        auto skin=overrides::find_skin_model(record->name);
        if(!diagnostic&&!skin)return;
        std::array<float,16> matrix{},camera_matrix{};
        if(!m.contains(camera,64))return;
        for(unsigned i=0;i<16;++i){matrix[i]=std::bit_cast<float>(m.aot_load32(c.gpr[7]+i*4));
            camera_matrix[i]=std::bit_cast<float>(m.aot_load32(camera+i*4));
            if(!std::isfinite(matrix[i])||!std::isfinite(camera_matrix[i]))return;}
        overrides::PoseIdentity identity{{record->record,record->key,record->vertices,record->indices,
            record->vertex_count,record->index_count},c.gpr[4],c.gpr[5]};
        const auto count=m.aot_load32(record->record+12);
        auto runtime_pose=skin?overrides::runtime_pose_store.submit(identity,count,c.gpr[6],matrix,camera_matrix):nullptr;
        if(skin&&count<=256&&c.gpr[6]<count){
            const auto table=m.aot_load32(record->record);
            if(m.contains(table,count*16)){
                const auto entry=table+c.gpr[6]*16, length=m.aot_load32(entry+4);
                const auto va=record->vertices+std::uint64_t(m.aot_load32(entry+8))*record->stride;
                const auto ia=record->indices+std::uint64_t(m.aot_load32(entry+12))*2;
                if(va<=0xffffffff&&ia<=0xffffffff&&length<=65533)
                    overrides::command_submission(identity,count,c.gpr[6],static_cast<unsigned>(va),static_cast<unsigned>(ia),
                        length?((4u<<16)|(length+2)):0,runtime_pose);
            }
        }
        if(!diagnostic)return;
        auto pose=overrides::diagnostic_pose_store.submit(identity,count,c.gpr[6],matrix,camera_matrix);
        static std::ofstream f(output,std::ios::trunc);if(!f)return;
        f<<std::setprecision(9)<<"{\"sample\":"<<++samples<<",\"name\":"<<std::quoted(record->name)
            <<",\"record\":"<<address<<",\"part\":"<<c.gpr[6]<<",\"caller\":"<<c.gpr[31]
            <<",\"completed_pose\":"<<(pose?pose->serial:0)
            <<",\"runtime_pose\":"<<(runtime_pose?runtime_pose->serial:0);
        auto array=[&](const char* name,const auto& values){f<<",\""<<name<<"\":[";
            for(std::size_t i=0;i<values.size();++i){if(i)f<<',';f<<values[i];}f<<']';};
        array("registers",c.gpr);array("matrix",matrix);array("camera",camera_matrix);
        f<<"}\n";f.flush();
    }catch(...){}
}
inline void transforms(const psprecomp::GuestMemory& memory,std::uint32_t va,std::uint32_t ia,
    std::uint32_t type,std::uint32_t primitive,const std::array<float,12>& world,
    const std::array<float,12>& view,const std::array<float,16>& projection) noexcept {
    static const char* output=std::getenv("RENEGADE_TRACE_MODEL_TRANSFORMS");
    if(!output||!*output)return;
    try {
        static std::uint64_t sequence=0;++sequence;
        auto part=render_resources::resolve_part(memory,va,ia,primitive);
        const bool matched=part.resource!=nullptr;
        if(!matched){
            if(((type>>11)&3)!=2)return; // only 16-bit indexed candidates
            const Record* found=nullptr;
            for(const auto& [base,r]:records)if(ia>=r.indices&&std::uint64_t(ia)<r.indices+std::uint64_t(r.index_count)*2&&render_resources::is_live(memory,r)){found=&r;break;}
            if(!found)return;const auto& candidate=*found;
            auto table=memory.aot_load32(candidate.record),count=memory.aot_load32(candidate.record+12);
            if(count>4096||!memory.contains(table,count*16))return;
            // Diagnostic candidate only: production matching is unchanged.
            for(unsigned i=0;i<count;++i)if(candidate.indices+std::uint64_t(memory.aot_load32(table+i*16+12))*2==ia){part={&candidate,i};break;}
            if(!part.resource)return;
        }
        const auto& r=*part.resource;
        auto pose=overrides::diagnostic_pose_store.match({r.record,r.key,r.vertices,r.indices,r.vertex_count,r.index_count},part.slot,world);
        static std::map<std::pair<std::uint32_t,unsigned>,unsigned> samples;
        const auto id=std::make_pair(r.key,part.slot);
        if(samples.size()>=4096&&!samples.contains(id))return;
        if(samples[id]>=4)return;
        for(float n:world)if(!std::isfinite(n))return;
        for(float n:view)if(!std::isfinite(n))return;
        for(float n:projection)if(!std::isfinite(n))return;
        static std::ofstream f(output,std::ios::trunc);if(!f)return;
        ++samples[id];f<<std::setprecision(9)<<"{\"sequence\":"<<sequence<<",\"name\":"<<std::quoted(r.name)
            <<",\"key\":"<<r.key<<",\"part\":"<<part.slot
            <<",\"part_count\":"<<memory.aot_load32(r.record+12)<<",\"vtype\":"<<type
            <<",\"matched\":"<<(matched?"true":"false")<<",\"vertex_address\":"<<va
            <<",\"vertex_base\":"<<r.vertices<<",\"index_address\":"<<ia<<",\"primitive\":"<<primitive
            <<",\"pose_serial\":"<<(pose?pose->serial:0);
        auto entry=memory.aot_load32(r.record)+part.slot*16;
        f<<",\"part_words\":[";for(unsigned i=0;i<4;++i){if(i)f<<',';f<<memory.aot_load32(entry+i*4);}f<<']';
        auto array=[&](const char* name,const auto& values){f<<",\""<<name<<"\":[";
            for(std::size_t i=0;i<values.size();++i){if(i)f<<',';f<<values[i];}f<<']';};
        array("world",world);array("view",view);array("projection",projection);f<<"}\n";f.flush();
    }catch(...){}
}
}
