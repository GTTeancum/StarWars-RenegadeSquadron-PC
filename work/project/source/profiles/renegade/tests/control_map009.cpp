#include "../host/control_context009.hpp"
#include "../host/modern_input008.hpp"
#include "psprecomp/runtime.hpp"
#include <array>
#include <bit>
#include <cstring>
#include <iostream>
#include <memory>
namespace psprecomp{void recomp_unit_0073(Runtime&,AllegrexContext&);}
int main(){
 auto rt=std::make_unique<psprecomp::Runtime>();auto& m=rt->memory();
 constexpr unsigned map=0x08810000,ptrs=0x08810100,scales=0x08810200,values=0x08810300,stack=0x08812000;
 renegade::context009::install(*rt,psprecomp::recomp_unit_0073);
 unsigned comparisons=0;
 for(unsigned pc:{0x0889679Cu,0x088968E8u})for(unsigned caller:{0x08A5E3D4u,0x08A5E3FCu,0x09000000u})
 for(unsigned count:{0u,1u,28u})for(bool mappings:{false,true}){
  auto prepare=[&]{m.zero(map,0x400);m.zero(stack-64,128);
   m.store32(map,count);m.store32(map+4,mappings?ptrs:0);m.store32(map+8,scales);m.store32(map+12,values);
   for(unsigned i=0;i<28;++i){m.store32(scales+4*i,std::bit_cast<unsigned>(0.5f+i*.01f));m.store32(values+4*i,0x3f000000u+i*117);}
  };
  psprecomp::AllegrexContext a{};
  for(unsigned i=1;i<32;++i)a.gpr[i]=0x5a000000+i;
  for(unsigned i=0;i<32;++i)a.fpr[i]=std::bit_cast<float>(0x3f800000u+i*97);
  a.pc=pc;a.gpr[4]=map;a.gpr[29]=stack;a.gpr[31]=caller;auto b=a;
  prepare();psprecomp::recomp_unit_0073(*rt,a);
  std::array<unsigned,256> data{};std::array<unsigned,32> saved_stack{};
  for(unsigned i=0;i<data.size();++i)data[i]=m.load32(map+4*i);
  for(unsigned i=0;i<saved_stack.size();++i)saved_stack[i]=m.load32(stack-64+4*i);
  prepare();renegade::context009::original_map_operation(*rt,b);
  if(std::memcmp(&a,&b,sizeof(a))){std::cerr<<"Register mismatch pc="<<std::hex<<pc<<" caller="<<caller<<"\n";return 1;}
  for(unsigned i=0;i<data.size();++i)if(data[i]!=m.load32(map+4*i)){std::cerr<<"Map memory mismatch\n";return 1;}
  for(unsigned i=0;i<saved_stack.size();++i)if(saved_stack[i]!=m.load32(stack-64+4*i)){std::cerr<<"Stack memory mismatch\n";return 1;}
  ++comparisons;
 }
 std::cout<<"original_AOT_map_update_reset_equivalence="<<comparisons<<" register/map/stack contexts passed\n";
}
