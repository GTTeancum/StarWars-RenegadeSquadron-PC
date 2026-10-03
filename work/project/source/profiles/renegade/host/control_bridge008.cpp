#include "control_context009.hpp"
#include "modern_input008.hpp"
#include "psprecomp/runtime.hpp"
#include <array>
#include <bit>
#include <cstdlib>
#include <iostream>
namespace renegade::input008 {
namespace {
std::array<std::array<unsigned,28>,2> last_bits;
bool first=true;
unsigned logged=0;
float apply_turret(unsigned action,float original) {
 const Frame f=current();
 if(!modern_enabled()||!f.active)return original;
 // ULUS10292 turret constructor 0x08A60098 and native input-table probes:
 // analog axes 0..3, original R held 8, Up edge 9, Cross held 13.
 switch(action) {
 case 0:case 2:return f.look_x;
 case 1:case 3:return f.look_y;
 case 8:return f.enabled&&f.left_trigger>trigger_threshold()?1.f:0.f;
 case 9:return pending_action(24)?1.f:0.f;
 case 13:return f.enabled&&f.right_trigger>trigger_threshold()?1.f:0.f;
 default:return original;
 }
}
float apply_action(unsigned action,float original) {
 const Frame f=current();
 if(!modern_enabled()||!f.active)return original;
 const auto held=[&](Button b){return f.enabled && (f.buttons&bit(b))!=0;};
 // Action numbering verified from the original ULUS10292 binding constructor.
 // The caller's own input gate, pitch inversion, camera limits and simulation
 // still run normally. Supply input, never positions or camera matrices.
 switch(action) {
 case 0:case 2:return f.look_x;
 case 1:case 3:return f.look_y;
 case 4:return f.move_y;
 case 5:return f.move_x;
 case 8:return f.enabled&&f.right_trigger>trigger_threshold()?1.f:0.f;
 case 9:return held(RightShoulder)?1.f:0.f;
 case 10:return held(X)?1.f:0.f;
 case 16:return f.enabled&&f.left_trigger>trigger_threshold()?1.f:0.f;
 case 21:return held(LeftStick)?1.f:0.f;
 // Native jetpack trace: original Triangle drives 26 (rise), Circle drives
 // 27 (descend). Keep these held inputs separate from jump/jetpack toggle.
 case 26:return held(Up)?1.f:0.f;
 case 27:return held(Down)?1.f:0.f;
 case 11:case 17:case 18:case 20:case 22:case 23:case 24:case 25:
  return pending_action(action)?1.f:0.f;
 default:return original;
 }
}
}
void action_getter(psprecomp::Runtime& rt,psprecomp::AllegrexContext& c) {
 const auto map=c.gpr[4],action=c.gpr[5],caller=c.gpr[31];
 // Literal register/memory semantics of leaf 0x088968BC, including out-of-range
 // behavior and original integer temporaries. No guest memory writes.
 c.gpr[2]=rt.memory().load32(map);
 const auto count=c.gpr[2];
 c.gpr[3]=action<<2;
 c.fpr[0]=0.f;
 c.gpr[5]=action<c.gpr[2]?1:0;
 if(c.gpr[5]) {
  c.gpr[2]=rt.memory().load32(map+12)+c.gpr[3];
  c.fpr[0]=std::bit_cast<float>(rt.memory().load32(c.gpr[2]));
 }
 const float original=c.fpr[0];
 const bool infantry=caller==0x08A5F164;
 const bool turret=caller==0x08A60064&&count==17;
 // Restrict substitution to verified readers; preserve original leaf effects.
 if((infantry||turret) && c.gpr[5] && action<28) {
   const bool owns_input=!modern_enabled()||context009::allow_infantry(map);
   if(owns_input)c.fpr[0]=turret?apply_turret(action,original):apply_action(action,original);
 }
 if(std::getenv("RENEGADE_TRACE_ACTIONS")&&(infantry||turret)&&action<28&&logged<12000) {
  if(first){for(auto& row:last_bits)row.fill(0x7fffffffu);first=false;}
  auto& previous=last_bits[turret?1:0];
  const unsigned bits=std::bit_cast<unsigned>(c.fpr[0]);
  if(bits!=previous[action]) {
   ++logged;previous[action]=bits;
   std::cerr<<"[action008] frame="<<frame_number()<<" id="<<action<<" value="<<c.fpr[0]
    <<" original="<<original<<" modern="<<(modern_enabled()&&current().active)<<" context="<<(turret?"turret":"infantry")
    <<" self=0x"<<std::hex<<c.gpr[17]<<" map=0x"<<map<<std::dec<<"\n";
  }
 }
 c.pc=caller;
}
}
namespace renegade {
void install_control_bridge008(psprecomp::Runtime& rt) {
 input008::reset();
 context009::reset();
 if(!input008::modern_enabled()&&!std::getenv("RENEGADE_TRACE_ACTIONS"))return;
 rt.register_function(0x088968BC,input008::action_getter,"renegade_infantry_input008");
 std::cerr<<"[input008] "<<(input008::modern_enabled()?"modern infantry and turret opt-in":"read-only original action trace")
          <<"; no game-state writes\n";
}
}
