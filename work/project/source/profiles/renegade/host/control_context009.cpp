#include "control_context009.hpp"
#include "modern_input008.hpp"
#include "psprecomp/runtime.hpp"
#include <map>
#include <iostream>
#include <cstdlib>
namespace renegade::context009 {
namespace {
struct Map {bool updated=true;std::uint64_t frame=0;};
std::map<std::uint32_t,Map> maps;
std::uint32_t infantry_map=0;
OriginalMapUnit original=nullptr;
unsigned log_count=0;
}
void reset(){maps.clear();infantry_map=0;log_count=0;}
void observe_map(std::uint32_t map,bool updated,std::uint32_t caller) {
 // Verified original actor input-handler callsites, not AvP structure offsets.
 if((updated&&caller!=0x08A5E3D4u)||(!updated&&caller!=0x08A5E3FCu))return;
 auto it=maps.find(map);
 if(it==maps.end()){
  if(maps.size()>=256)return; // Bounded table; untracked maps fall back when full.
  it=maps.emplace(map,Map{}).first;
 }
 bool transition=it->second.updated!=updated;
 it->second={updated,input008::frame_number()};
 if(map==infantry_map&&(!updated||transition))input008::quarantine_held_actions009();
 if(std::getenv("RENEGADE_TRACE_CONTEXTS")&&log_count<2000&&(!updated||transition)){
  ++log_count;std::cerr<<"[ownership009] frame="<<input008::frame_number()<<" map=0x"<<std::hex<<map
   <<std::dec<<" updated="<<updated<<" tracked="<<(map==infantry_map)<<"\n";
 }
}
bool allow_infantry(std::uint32_t map) {
 if(map!=infantry_map){
  if(infantry_map)input008::quarantine_held_actions009();
  infantry_map=map;
 }
 auto it=maps.find(map);
 if(it==maps.end()&&maps.size()>=256){input008::quarantine_held_actions009();return false;}
 if(it!=maps.end()&&!it->second.updated){input008::quarantine_held_actions009();return false;}
 return true;
}
void original_map_operation(psprecomp::Runtime& rt,psprecomp::AllegrexContext& c) {
 if(!original)throw psprecomp::Error("Missing original control-map unit");
 const auto pc=c.pc;
 if(input008::modern_enabled())observe_map(c.gpr[4],pc==0x0889679Cu,c.gpr[31]);
 // Execute the original AOT routine including its register, stack, and memory effects.
 // No later-engine code is substituted for the original mapping/reset implementation.
 original(rt,c);
}
void install(psprecomp::Runtime& rt,OriginalMapUnit callback) {
 reset();original=callback;
 if(!input008::modern_enabled())return;
 if(!original)throw psprecomp::Error("Missing original control-map unit");
 rt.register_function(0x0889679Cu,original_map_operation,"original_map_update_with_ownership009");
 rt.register_function(0x088968E8u,original_map_operation,"original_map_reset_with_ownership009");
 std::cerr<<"[ownership009] following original actor map update/reset; held input requires release after ownership change\n";
}
}
