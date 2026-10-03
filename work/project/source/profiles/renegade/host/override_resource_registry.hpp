#pragma once
#include "psprecomp/guest_memory.hpp"
#include <cstddef>
#include <cstdint>
#include <map>
#include <string>
namespace renegade::render_resources {
struct Record {
    std::string name;
    std::uint32_t record{},key{},vertices{},indices{},vertex_count{},index_count{},stride{};
    unsigned observations{};
};
inline std::map<std::uint32_t,Record> records;
inline constexpr std::size_t capacity=4096;
bool is_live(const psprecomp::GuestMemory&,const Record&) noexcept;
// Never retain pointers into guest memory. Reused vertex addresses replace their
// registration even at capacity. Evict only entries no longer matching the live
// guest allocation; if all slots are live, new unregistered models stay original.
bool register_record(const psprecomp::GuestMemory&,const Record&);
const Record* find_record(const psprecomp::GuestMemory&,std::uint32_t record_address) noexcept;
struct Part {const Record* resource{};unsigned slot{};};
Part resolve_part(const psprecomp::GuestMemory&,std::uint32_t vertex_address,
                  std::uint32_t index_address,std::uint32_t primitive) noexcept;
}
