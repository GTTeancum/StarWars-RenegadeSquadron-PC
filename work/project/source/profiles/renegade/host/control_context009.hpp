#pragma once
#include <cstdint>
namespace psprecomp {class Runtime;struct AllegrexContext;}
namespace renegade::context009 {
using OriginalMapUnit=void(*)(psprecomp::Runtime&,psprecomp::AllegrexContext&);
void reset();
void observe_map(std::uint32_t map,bool updated,std::uint32_t caller);
bool allow_infantry(std::uint32_t map);
void original_map_operation(psprecomp::Runtime&,psprecomp::AllegrexContext&);
void install(psprecomp::Runtime&,OriginalMapUnit);
}
