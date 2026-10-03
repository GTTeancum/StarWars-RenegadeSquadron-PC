#include "../host/control_context009.hpp"
#include "../host/modern_input008.hpp"
#include "../host/test_environment010.hpp"
#include "psprecomp/runtime.hpp"
#include <bit>
#include <iostream>
#include <memory>
using namespace renegade;
using namespace renegade::input008;
int main(){
 unsigned checks=0,fail=0;auto ck=[&](bool ok,const char* why){++checks;if(!ok){++fail;std::cerr<<"FAIL "<<why<<'\n';}};
 test010::set_environment("RENEGADE_CONTROLS","modern");
 auto rt=std::make_unique<psprecomp::Runtime>();auto& m=rt->memory();
 constexpr unsigned map=0x08810000,values=0x08811000,infantry=0x08820000,iv=0x08821000,caller=0x08A60064;
 m.store32(map,17);m.store32(map+12,values);m.zero(values,17*4);
 m.store32(infantry,28);m.store32(infantry+12,iv);m.zero(iv,28*4);
 auto get=[&](unsigned a,unsigned from=0x08A60064,unsigned table=0x08810000){
  psprecomp::AllegrexContext c{};c.gpr[4]=table;c.gpr[5]=a;c.gpr[31]=from;
  action_getter(*rt,c);
  ck(c.pc==from&&c.gpr[3]==a*4&&c.gpr[5]==(a<m.load32(table)),"leaf registers preserved");
  if(a<m.load32(table))ck(c.gpr[2]==m.load32(table+12)+a*4,"leaf value pointer preserved");
  return c.fpr[0];
 };
 reset(Config{});context009::reset();RawPad p{true,true};accept_sample(1,p);get(0,0x08A5F164,infantry);
 p.buttons=bit(X);p.rt=32767;accept_sample(2,p);
 ck(get(9)==0&&get(13)==0,"entering turret quarantines held use and fire");
 p.buttons=0;p.rt=0;accept_sample(3,p);
 p.rx=22000;p.ry=-18000;p.lt=p.rt=32767;p.buttons=bit(X);accept_sample(4,p);
 ck(get(0)==current().look_x&&get(2)==current().look_x&&get(0)>0,"turret yaw");
 ck(get(1)==current().look_y&&get(3)==current().look_y&&get(1)!=0,"turret pitch");
 ck(get(8)==1&&get(13)==1,"turret aim and fire");
 ck(get(9)==1&&get(9)==1,"use survives repeated readers in same frame");
 accept_sample(5,p);ck(get(9)==0,"use does not repeat while held");
 for(unsigned a:{4u,5u,6u,7u,10u,11u,12u,14u,15u,16u}){
  m.store32(values+a*4,std::bit_cast<unsigned>(.25f));ck(get(a)==.25f,"unmapped turret actions preserved");
 }
 ck(get(13,0x12345678)==0,"foreign reader unchanged");
 m.store32(map,28);ck(get(13)==0,"unexpected table shape unchanged");m.store32(map,17);
 ck(get(17)==0,"out of bounds remains zero");
 context009::observe_map(map,false,0x08A5E3FC);ck(get(13)==0,"disabled map remains original");
 context009::observe_map(map,true,0x08A5E3D4);ck(get(13)==0,"regain requires trigger release");
 p.rt=p.lt=0;p.buttons=0;accept_sample(6,p);p.rt=32767;accept_sample(7,p);ck(get(13)==1,"fire rearms");
 ck(get(8,0x08A5F164,infantry)==0,"return to infantry quarantines held fire");
 p.rt=0;accept_sample(8,p);p.rt=32767;accept_sample(9,p);ck(get(8,0x08A5F164,infantry)==1,"infantry fire rearms");
 for(unsigned a:{0u,1u,2u,3u,8u,9u,13u})ck(m.load32(values+a*4)==0,"guest mapped values never written");
 std::cout<<"turret013_checks="<<checks<<" failures="<<fail<<'\n';return fail?1:0;
}
