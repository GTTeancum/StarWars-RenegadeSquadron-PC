#include "psprecomp/runtime.hpp"
#include "psprecomp/decoder.hpp"
#include "ge_transfer.hpp"
#include <iostream>
#include <random>
#include <cstring>
using namespace psprecomp;
static unsigned checks=0;
void check(bool b,const char* m){++checks;if(!b)throw Error(m);}
unsigned index(unsigned r,unsigned n,unsigned i){return AllegrexContext::vfpu_vector_lane_index(r,n,i);}
void put(AllegrexContext& c,unsigned r,unsigned n,unsigned i,std::uint32_t v){c.vfpu[index(r,n,i)]=std::bit_cast<float>(v);}
std::uint32_t get(const AllegrexContext& c,unsigned r,unsigned n,unsigned i){return std::bit_cast<std::uint32_t>(c.vfpu[index(r,n,i)]);}
int main(){try{
 GuestMemory m; std::mt19937 rng(10292);auto fast=m.aot_fast_view();
 for(unsigned i=0;i<4096;++i){auto v=rng();fast.aot_store32(0x40010000u+4*i,v);check(m.load32(0x10000u+4*i)==v,"scratch alias");check(m.raw_pointer(0x10000u+4*i,4)!=nullptr,"scratch raw pointer");}
 check(!m.contains(0x13fffu,2),"scratch boundary");check(m.raw_pointer(0x13fff,2)==nullptr,"scratch pointer boundary");
 check(m.load32(0x08000000u)==0 && m.load32(0x04000000u)==0,"scratch isolation");
 for(unsigned reg=0;reg<64;++reg)for(unsigned pos=0;pos<16;++pos)for(bool right:{false,true})for(bool store:{false,true}){
  AllegrexContext c;c.eat_vfpu_prefixes();for(unsigned i=0;i<128;++i)c.vfpu[i]=std::bit_cast<float>(0x81000000u+i);
  c.vfpu_ctrl[0]=0xabcdef;c.vfpu_ctrl[1]=0x123456;c.vfpu_ctrl[2]=0x765432;
  auto old=c;for(unsigned i=0;i<4;++i)m.store32(0x10000+4*i,0x71234560+i);
  vfpu_partial_memory(m,c,0x40010000+pos,reg,right,store);
  unsigned word=pos/4, cnt=right?4-word:word+1, lane=right?0:3-word, first=right?word:0;
  for(unsigned i=0;i<4;++i){
   auto expected=(!store && i>=lane && i<lane+cnt)?0x71234560u+first+i-lane:get(old,reg,4,i);
   check(get(c,reg,4,i)==expected,"partial register result");
   auto expected_mem=(store && i>=first && i<first+cnt)?get(old,reg,4,lane+i-first):0x71234560u+i;
   check(m.load32(0x10000+4*i)==expected_mem,"partial memory result");
  }
  check(c.vfpu_ctrl==old.vfpu_ctrl,"partial prefix preservation");
 }
 {AllegrexContext c;c.eat_vfpu_prefixes();bool rejected=false;try{vfpu_partial_memory(m,c,0x14000,0,true,true);}catch(const Error&){rejected=true;}check(rejected,"partial bounds reject");}
 for(unsigned op=28;op<=31;++op) for(unsigned n:{2u,4u}){if(op<30 && n!=4)continue;
  for(unsigned r=0;r<128;++r){AllegrexContext c;c.eat_vfpu_prefixes(); std::uint32_t vals[4];for(unsigned i=0;i<n;++i){vals[i]=rng();put(c,r,n,i,vals[i]);}
   unsigned group=op<30?4:2,width=op<30?8:16;unsigned d=(r+13)%128;
   vfpu_pack_integer(c,d,r,n,op);
   for(unsigned i=0;i<n/group;++i){std::uint32_t expected=0;for(unsigned j=0;j<group;++j){auto v=vals[i*group+j];if(!(op&1)&&static_cast<std::int32_t>(v)<0)v=0;auto shift=op&1?(32-width):(31-width);expected|=((v>>shift)&(width==8?255:65535))<<(width*j);}check(get(c,d,n/group,i)==expected,"integer packing");}
   check(c.vfpu_ctrl[0]==0xe4 && c.vfpu_ctrl[1]==0xe4 && c.vfpu_ctrl[2]==0,"prefix consumption");
  }
 }
 for(unsigned op:{0u,1u,8u,9u})for(unsigned r=0;r<128;++r){AllegrexContext c;c.eat_vfpu_prefixes();float in[]={3,-5,7,1};for(unsigned i=0;i<4;++i)c.vfpu[index(r,4,i)]=in[i];vfpu_sort_sign(c,(r+19)%128,r,4,op);float want[4];if(op==0){float t[]={-5,3,1,7};std::memcpy(want,t,16);}if(op==1){float t[]={1,-5,7,3};std::memcpy(want,t,16);}if(op==8){float t[]={3,-5,7,1};std::memcpy(want,t,16);}if(op==9){float t[]={3,7,-5,1};std::memcpy(want,t,16);}for(unsigned i=0;i<4;++i)check(c.vfpu[index((r+19)%128,4,i)]==want[i],"sorting");}
 for(unsigned r=0;r<128;++r)for(unsigned n=1;n<=4;++n){AllegrexContext c;c.eat_vfpu_prefixes();std::uint32_t v[]={0,0x80000000,0xbf800000,0x3f800000};for(unsigned i=0;i<n;++i)put(c,r,n,i,v[i]);vfpu_sort_sign(c,(r+21)%128,r,n,10);for(unsigned i=0;i<n;++i)check(get(c,(r+21)%128,n,i)==(i<2?0:v[i]),"sign");}
 for(unsigned fmt=0;fmt<2;++fmt)for(unsigned off=0;off<4;++off){std::array<std::uint32_t,256> c{};c[0xb2]=0x10000;c[0xb3]=16;c[0xb4]=0x10000+off*2;c[0xb5]=16;c[0xea]=fmt;c[0xee]=7|(3<<10);c[0xeb]=2|(1<<10);c[0xec]=1|(2<<10);unsigned bpp=fmt?4:2;for(unsigned i=0;i<1024;++i)m.store8(0x10000+i,std::uint8_t(i*7));std::uint8_t old[1024];for(unsigned i=0;i<1024;++i)old[i]=m.load8(0x10000+i);check(renegade::ge_transfer(m,c)==8*4*bpp,"transfer count");for(unsigned y=0;y<4;++y)for(unsigned x=0;x<8*bpp;++x)check(m.load8(0x10000+off*2+((y+2)*16+1)*bpp+x)==old[((y+1)*16+2)*bpp+x],"overlapping transfer");}
 check(decode_allegrex(0xF7BC0092).kind==OpcodeKind::VPartial,"SVR.Q decode");
 check(decode_allegrex(0xD03C8080).kind==OpcodeKind::Vi2x,"pack decode");
 std::cout<<"PASS "<<checks<<" scratchpad/VFPU/GE transfer checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<"\n";return 1;}}
