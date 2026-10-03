#pragma once
#include <array>
#include <cstdint>
#include <filesystem>
#include <map>
namespace renegade::materials009 {
// Diagnostic observation only. No guest-memory reads, writes or raster changes.
struct Counts {std::uint64_t draws{},vertices{},first{},last{};};
struct Key {
 std::uint32_t vtype{},lighting{},lightmode{},texture{},clear{},material_update{},specular_rgb{},light_mask{};
 auto operator<=>(const Key&)const=default;
};
class Collector {
 std::map<Key,Counts> rows_;
 std::uint64_t dropped_{};
public:
 void observe(std::uint64_t frame,const std::array<std::uint32_t,256>&,std::uint32_t count);
 const auto& rows()const{return rows_;}
 std::uint64_t dropped()const{return dropped_;}
 void write(const std::filesystem::path&)const;
};
void begin_from_environment(std::uint64_t(*frame)());
void observe(const std::array<std::uint32_t,256>&,std::uint32_t count);
void finish();
}
