#include "ge_stencil.hpp"
#include "ge_renderer.hpp"
#include "psprecomp/guest_memory.hpp"
#include <bit>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <array>
namespace {
unsigned checks=0;
void check(bool condition,const char* label) { ++checks; if(!condition) throw std::runtime_error(label); }
unsigned quantize(unsigned x,unsigned format) { return format==3 ? x : format==2 ? (x>>4)*17 : format==1 ? (x>=128 ? 255 : 0) : 0; }
unsigned pack(unsigned rgba,unsigned format) {
 unsigned r=rgba&255,g=(rgba>>8)&255,b=(rgba>>16)&255,a=rgba>>24;
 if(format==3)return rgba;
 if(format==2)return (r>>4)|((g>>4)<<4)|((b>>4)<<8)|((a>>4)<<12);
 if(format==1)return (r>>3)|((g>>3)<<5)|((b>>3)<<10)|((a>>7)<<15);
 return (r>>3)|((g>>2)<<5)|((b>>3)<<11);
}
struct Fixture {
 psprecomp::GuestMemory memory;
 std::array<std::uint32_t,256> c{};
 vcs::GeTransformState transform{};
 unsigned format{},kind{};
 std::uint64_t revision{};
 static constexpr unsigned fb=0x04000000, db=0x04010000, vertices=0x08801000;
 Fixture(){vcs::reset_ge_transform_state(transform);}
 void setup(unsigned fmt,unsigned primitive,unsigned old=0x50123456) {
  format=fmt;kind=primitive;c.fill(0);
  c[0x9c]=0;c[0x9d]=8;c[0x9e]=0x10000;c[0x9f]=8;c[0xd2]=fmt;c[0xd5]=3|(3<<10);
  c[0x12]=0x800000|(7<<2)|(3<<7);c[0xde]=1;c[0xe7]=0;
  for(unsigned n=0;n<32;++n){if(fmt==3)memory.aot_store32(fb+n*4,old);else memory.aot_store16(fb+n*2,pack(old,fmt));memory.aot_store16(db+n*2,100);}
  vertex(0,0,0,200,0x99336699);vertex(1,primitive==3?4:1,primitive==3?0:1,200,0x99336699);vertex(2,0,4,200,0x99336699);
 }
 void vertex(unsigned index,float x,float y,float z,unsigned color) {
  auto a=vertices+index*16;memory.aot_store32(a,color);memory.aot_store32(a+4,std::bit_cast<unsigned>(x));memory.aot_store32(a+8,std::bit_cast<unsigned>(y));memory.aot_store32(a+12,std::bit_cast<unsigned>(z));
 }
 unsigned raw() {return format==3?memory.aot_load32(fb):memory.aot_load16(fb);}
 unsigned alpha(){unsigned v=raw();return format==3?v>>24:format==2?(v>>12)*17:format==1?(v>>15)*255:0;}
 void stencil(unsigned fn,unsigned ref,unsigned mask=255,unsigned fail=0,unsigned zfail=0,unsigned zpass=0){c[0x24]=1;c[0xdc]=fn|(ref<<8)|(mask<<16);c[0xdd]=fail|(zfail<<8)|(zpass<<16);}
 void draw(){vcs::GeRenderStats stats{};std::string error;check(vcs::render_ge_primitive(memory,c,transform,vertices,0,(kind<<16)|(kind==6?2:kind==3?3:1),stats,error,1,++revision),error.c_str());}
};
}
int main(){try{
 // Independent exhaustive arithmetic expectations, including saturating endpoints.
 for(unsigned f=0;f<4;++f)for(unsigned value=0;value<256;++value)for(unsigned op=0;op<6;++op){
  unsigned stored=quantize(value,f),maximum=f==3?255:f==2?15:f==1?1:0;
  unsigned raw=maximum?stored*maximum/255:0,desired=raw;
  if(op==1)desired=0;if(op==2)desired=maximum?0xa7*maximum/255:0;
  if(op==3)desired=maximum-raw;if(op==4)desired=raw<maximum?raw+1:maximum;if(op==5)desired=raw?raw-1:0;
  unsigned expected=maximum?desired*255/maximum:0;
  if(op==2)expected=quantize(0xa7,f);
  check(quantize(vcs::ge_stencil_operation(f,op,stored,0xa7),f)==expected,"stencil operation arithmetic");
 }
 for(unsigned mask: {0u,15u,0xf0u,255u})for(unsigned ref=0;ref<256;ref+=17)for(unsigned value=0;value<256;value+=17)for(unsigned fn=0;fn<8;++fn){
  unsigned a=ref&mask,b=value&mask;bool results[]={false,true,a==b,a!=b,a<b,a<=b,a>b,a>=b};
  vcs::GeStencilState s{true,static_cast<unsigned char>(fn),static_cast<unsigned char>(ref),static_cast<unsigned char>(mask),0,0,0};
  check(vcs::ge_stencil_compare(s,value)==results[fn],"masked comparison/order");
 }
 auto ptr=std::make_unique<Fixture>();auto& f=*ptr;
 for(unsigned kind: {0u,3u,6u}) {
  for(unsigned fmt=0;fmt<4;++fmt) {
   f.setup(fmt,kind);auto old=f.raw();f.draw();check(f.alpha()==quantize(0x50,fmt),"disabled stencil must preserve alpha");check((f.raw()&(fmt==3?0xffffff:fmt==2?0xfff:fmt==1?0x7fff:0xffff))==(pack(0x00336699,fmt)&(fmt==3?0xffffff:fmt==2?0xfff:fmt==1?0x7fff:0xffff)),"normal RGB write");
   for(unsigned op=0;op<6;++op){
    f.setup(fmt,kind);old=f.raw();f.stencil(0,0xa7,255,op,0,0);f.draw();
    check(f.alpha()==quantize(vcs::ge_stencil_operation(fmt,op,quantize(0x50,fmt),0xa7),fmt),"stencil-fail operation");
    check((f.raw()& (fmt==3?0xffffff:fmt==2?0xfff:fmt==1?0x7fff:0xffff))==(old & (fmt==3?0xffffff:fmt==2?0xfff:fmt==1?0x7fff:0xffff)),"stencil-fail RGB preserved");check(f.memory.aot_load16(Fixture::db)==100,"stencil-fail must not write depth");
    f.setup(fmt,kind);old=f.raw();f.stencil(1,0xa7,255,0,op,0);f.c[0x23]=1;f.c[0xde]=0;f.draw();
    check(f.alpha()==quantize(vcs::ge_stencil_operation(fmt,op,quantize(0x50,fmt),0xa7),fmt),"depth-fail stencil operation");check(f.memory.aot_load16(Fixture::db)==100,"depth-fail no depth write");
    f.setup(fmt,kind);f.stencil(1,0xa7,255,0,0,op);f.draw();check(f.alpha()==quantize(vcs::ge_stencil_operation(fmt,op,quantize(0x50,fmt),0xa7),fmt),"depth-pass stencil operation");check(f.memory.aot_load16(Fixture::db)==200,"passed fragment writes depth");
   }
   // Framebuffer mask is per bit after format conversion, not a whole-channel flag.
   f.setup(fmt,kind);old=f.raw();f.stencil(1,0xa7,255,0,0,2);f.c[0xe8]=0x56a53c;f.c[0xe9]=0x90;f.draw();
   unsigned mask=pack(0x9056a53c,fmt);check(f.raw()==((old&mask)|(pack(0xa7336699,fmt)&~mask)),"packed per-bit write mask");
  }
  // The alpha test must reject before BOTH stencil and depth writes.
  f.setup(3,kind);auto old=f.raw();f.stencil(1,0xaa,255,0,0,2);f.c[0x22]=1;f.c[0xdb]=0xff0000;f.draw();check(f.raw()==old,"alpha-fail no stencil/color write");check(f.memory.aot_load16(Fixture::db)==100,"alpha-fail no depth write");
  // Clear bypasses all fragment tests and changes only requested buffers.
  f.setup(3,kind);f.stencil(0,0,255,1,1,1);f.c[0x22]=1;f.c[0xdb]=0xff0000;f.c[0x23]=1;f.c[0xde]=0;f.c[0xd3]=0x201;f.draw();check(f.raw()==0x99123456,"stencil-only clear");check(f.memory.aot_load16(Fixture::db)==100,"stencil-only clear leaves depth");
  // Changing stencil reference/ops without other GE state must invalidate cache.
  f.setup(3,kind);f.stencil(1,0x11,255,0,0,2);f.draw();check(f.alpha()==0x11,"initial cached stencil state");f.c[0xdc]=1|(0x22<<8)|(255<<16);f.draw();check(f.alpha()==0x22,"stencil-reference cache invalidation");f.c[0xdd]=3<<16;f.draw();check(f.alpha()==0xdd,"stencil-operation cache invalidation");f.c[0x24]=0;f.draw();check(f.alpha()==0xdd,"stencil-enable cache invalidation");
 }
 std::cout<<"Stencil/render regressions passed: "<<checks<<" checks\n";return 0;
 }catch(const std::exception& e){std::cerr<<"Stencil/render FAIL after "<<checks<<": "<<e.what()<<"\n";return 1;}}
