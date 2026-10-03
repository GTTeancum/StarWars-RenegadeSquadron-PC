#include "../host/control_context009.hpp"
#include "../host/modern_input008.hpp"
#include "psprecomp/runtime.hpp"
#include <iostream>
#include <cstdlib>
#include <memory>
#include <cstring>
#include <bit>
#include "../host/test_environment010.hpp"
using namespace renegade;
using namespace renegade::input008;
int main(){unsigned n=0,fail=0;auto ck=[&](bool yes,const char* why){++n;if(!yes){++fail;std::cerr<<"FAIL "<<why<<"\n";}};
 test010::set_environment("RENEGADE_CONTROLS","modern");
 constexpr unsigned map=0x08810000,other=0x08820000,update=0x08A5E3D4,clear=0x08A5E3FC;
 for(unsigned mask:{bit(A),bit(X),bit(Y),bit(LeftShoulder),bit(RightStick),bit(Up),bit(Down)}){
  reset(Config{});context009::reset();RawPad p{true,true};accept_sample(1,p);
  context009::observe_map(map,true,update);ck(context009::allow_infantry(map),"initial map owns input");
  p.buttons=mask;accept_sample(2,p);
  if(mask==bit(X))ck(pending_action(24)&&pending_action(25),"interaction delivered before same-frame ownership loss");
  context009::observe_map(map,false,clear);
  ck(!context009::allow_infantry(map),"original reset suspends modern input");
  for(unsigned a:{11u,18u,20u,22u,24u,25u})ck(!pending_action(a),"reset clears pending actions");
  accept_sample(3,p);context009::observe_map(map,true,update);
  ck(context009::allow_infantry(map),"original update restores ownership");
  ck(current().buttons==0,"held confirmation blocked after regain");
  p.buttons=0;accept_sample(4,p);p.buttons=mask;accept_sample(5,p);
  ck(current().buttons==mask,"release/repress restores action");
 }
 reset(Config{});context009::reset();RawPad p{true,true};accept_sample(1,p);
 context009::observe_map(map,true,update);context009::allow_infantry(map);
 p.lt=p.rt=32767;p.rx=22000;p.ly=-22000;accept_sample(2,p);
 context009::observe_map(map,false,clear);context009::observe_map(map,true,update);
 ck(current().left_trigger==0&&current().right_trigger==0,"both triggers blocked through transition");
 p.lt=p.rt=0;accept_sample(3,p);p.lt=p.rt=32767;accept_sample(4,p);
 ck(current().left_trigger==1&&current().right_trigger==1,"triggers rearm independently");
 ck(current().look_x>0&&current().move_y>0,"independent sticks remain available after regain");
 // Foreign map operations cannot consume current infantry events.
 p.buttons=0;accept_sample(5,p);p.buttons=bit(A);accept_sample(6,p);
 context009::observe_map(other,false,clear);ck(pending_action(11),"other map reset does not eat jump");
 p.buttons=0;accept_sample(7,p);p.buttons=bit(A);accept_sample(8,p);
 context009::observe_map(map,false,0x12345678);ck(context009::allow_infantry(map)&&pending_action(11),"foreign caller ignored");
 // Exact getter returns original values while suspended; no memory mutation.
 auto rt=std::make_unique<psprecomp::Runtime>();auto& m=rt->memory();constexpr unsigned values=0x08811000;
 m.store32(map,28);m.store32(map+12,values);m.zero(values,28*4);
 reset(Config{});context009::reset();p={true,true};accept_sample(10,p);context009::observe_map(map,true,update);context009::allow_infantry(map);
 p.rx=32767;p.ly=-32768;p.rt=32767;p.buttons=bit(A);accept_sample(11,p);context009::observe_map(map,false,clear);
 for(unsigned a:{0u,1u,2u,3u,4u,5u,8u,9u,10u,11u,16u,17u,18u,20u,21u,22u,23u,24u,25u,26u,27u}){
  psprecomp::AllegrexContext c{};c.gpr[4]=map;c.gpr[5]=a;c.gpr[31]=0x08A5F164;
  action_getter(*rt,c);ck(c.fpr[0]==0,"suspended action keeps original neutral");ck(c.gpr[3]==a*4&&c.gpr[5]==1&&c.pc==0x08A5F164,"original leaf temporaries preserved");
  ck(m.load32(values+a*4)==0,"no guest action-table write");
 }
 context009::observe_map(map,true,update);ck(!pending_action(11),"held popup confirm cannot jump on return");
 p.buttons=0;p.rt=0;accept_sample(12,p);p.buttons=bit(A);accept_sample(13,p);
 psprecomp::AllegrexContext c{};c.gpr[4]=map;c.gpr[5]=11;c.gpr[31]=0x08A5F164;action_getter(*rt,c);ck(c.fpr[0]==1,"fresh A jumps after menu");
 // A full bounded table must never accidentally re-enable an untracked map.
 context009::reset();
 for(unsigned i=0;i<256;++i)context009::observe_map(0x08900000u+i*16u,true,update);
 context009::observe_map(map,false,clear);
 ck(!context009::allow_infantry(map),"full ownership table falls back for untracked map");
 ck(!pending_action(11),"full-table fallback clears gameplay edge");
 std::cout<<"context009_checks="<<n<<" failures="<<fail<<"\n";return fail?1:0;
}
