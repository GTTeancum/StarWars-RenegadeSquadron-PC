#include "../host/modern_input008.hpp"
#include "psprecomp/runtime.hpp"
#include <bit>
#include <cstring>
#include <iostream>
#include <memory>
namespace psprecomp {void recomp_unit_0073(Runtime&,AllegrexContext&);}
int main(){
 auto rt=std::make_unique<psprecomp::Runtime>();auto& m=rt->memory();
 constexpr unsigned map=0x08810000,values=0x08811000;
 m.store32(map,28);m.store32(map+12,values);
 for(unsigned i=0;i<28;++i)m.store32(values+4*i,0x3f000000u+i*1987u);
 unsigned count=0;
 for(unsigned caller:{0x08A5F164u,0x09000000u,0x088969F8u}) {
  // Last caller is within the original native unit: omit it because the
  // generated dispatcher legitimately continues into the caller in that case.
  if(caller==0x088969F8u)continue;
  for(unsigned index:{0u,1u,2u,3u,4u,5u,6u,7u,8u,11u,16u,18u,21u,27u,28u,29u,0xffffffffu}) {
   psprecomp::AllegrexContext a{};
   for(unsigned i=1;i<32;++i)a.gpr[i]=0x5a000000+i;
   a.pc=0x088968BC;a.gpr[4]=map;a.gpr[5]=index;a.gpr[31]=caller;
   for(unsigned i=0;i<32;++i)a.fpr[i]=std::bit_cast<float>(0x3f800000u+i*117);
   auto b=a;
   psprecomp::recomp_unit_0073(*rt,a);
   renegade::input008::action_getter(*rt,b);
   if(std::memcmp(&a,&b,sizeof(a))!=0) {
    std::cerr<<"Leaf mismatch index="<<index<<" caller="<<std::hex<<caller
             <<" pc="<<a.pc<<"/"<<b.pc<<"\n";return 1;
   }
   ++count;
  }
 }
 std::cout<<"original_AOT_leaf_equivalence="<<count<<" contexts passed\n";
}
