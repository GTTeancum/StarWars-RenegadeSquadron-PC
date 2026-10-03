#include "override_resource_registry.hpp"
namespace renegade::render_resources {
bool is_live(const psprecomp::GuestMemory& m,const Record& r) noexcept {
    return r.record>=4 && m.contains(r.record-4,32) &&
        m.aot_load32(r.record-4)==r.key && m.aot_load32(r.record+4)==r.vertices &&
        m.aot_load32(r.record+8)==r.indices && m.aot_load32(r.record+16)==r.vertex_count &&
        m.aot_load32(r.record+20)==r.index_count &&
        (m.aot_load8(r.record+24)?24u:32u)==r.stride;
}
bool register_record(const psprecomp::GuestMemory& m,const Record& r){
    if(!is_live(m,r)||r.vertex_count>1000000||r.index_count>3000000||
       !m.contains(r.vertices,std::size_t(r.vertex_count)*r.stride)||
       !m.contains(r.indices,std::size_t(r.index_count)*2))return false;
    if(records.size()>=capacity&&!records.contains(r.vertices)){
        for(auto it=records.begin();it!=records.end();){
            if(!is_live(m,it->second))it=records.erase(it);else ++it;
        }
        if(records.size()>=capacity)return false;
    }
    records.insert_or_assign(r.vertices,r);return true;
}
const Record* find_record(const psprecomp::GuestMemory& m,std::uint32_t address) noexcept {
    // Cache identifiers, never pointers into a map that registration can mutate.
    // Every hit revalidates both its record address and its live guest identity.
    try {
        static std::map<std::uint32_t,std::uint32_t> vertices_by_record;
        if(auto cached=vertices_by_record.find(address);cached!=vertices_by_record.end()){
            auto found=records.find(cached->second);
            if(found!=records.end()&&found->second.record==address&&is_live(m,found->second))return &found->second;
            vertices_by_record.erase(cached);
        }
        for(const auto& [base,r]:records)if(r.record==address&&is_live(m,r)){
            if(vertices_by_record.size()>=capacity)vertices_by_record.clear();
            vertices_by_record[address]=base;return &r;
        }
    }catch(...){}
    return nullptr;
}
Part resolve_part(const psprecomp::GuestMemory& m,std::uint32_t va,
                         std::uint32_t ia,std::uint32_t primitive) noexcept {
    if((primitive>>16)!=4)return {};
    va=psprecomp::GuestMemory::canonical(va);ia=psprecomp::GuestMemory::canonical(ia);
    auto it=records.upper_bound(va);
    // Old allocations can leave an interior address in the registry after a
    // larger buffer reuses that region. Such entries must not hide a live owner.
    while(it!=records.begin()) { --it;
    const auto& r=it->second;
    // Most draws are outside a record's buffers. Reject those using owned
    // metadata before touching guest memory. Still validate every plausible
    // candidate, including earlier owners hidden by stale interior records.
    if(va<r.vertices||std::uint64_t(va)>=r.vertices+std::uint64_t(r.vertex_count)*r.stride||
       ia<r.indices||std::uint64_t(ia)>=r.indices+std::uint64_t(r.index_count)*2||!is_live(m,r))continue;
    auto table=m.aot_load32(r.record),count=m.aot_load32(r.record+12);
    if(count>4096||!m.contains(table,count*16))continue;
    for(unsigned part=0;part<count;++part){auto p=table+part*16;
        if(std::uint64_t(r.vertices)+m.aot_load32(p+8)*std::uint64_t(r.stride)==va&&
           std::uint64_t(r.indices)+m.aot_load32(p+12)*2ull==ia&&
           std::uint64_t(m.aot_load32(p+4))+2==(primitive&65535))return {&r,part};
    }
    }
    return {};
}
}
