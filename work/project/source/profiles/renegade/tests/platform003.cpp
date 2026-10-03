#include "psprecomp/runtime.hpp"
#include "stdio_eabi.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <vector>
namespace renegade {void install_platform_services(psprecomp::Runtime&);void install_psmf_services(psprecomp::Runtime&);bool interrupts_enabled(psprecomp::Runtime&);}
namespace psprecomp {void register_supplemental_functions(Runtime&);}
using namespace psprecomp;
static unsigned checks=0;static unsigned sort_callback_called=0;void ck(bool x,const char* msg){++checks;if(!x)throw Error(msg);}
void str(GuestMemory& m,unsigned addr,const std::string& s){for(unsigned i=0;i<=s.size();++i)m.store8(addr+i,i==s.size()?0:s[i]);}
unsigned call(Runtime& r,const char* lib,unsigned nid,std::initializer_list<unsigned> args){auto& c=r.cpu();c.pc=0x08800000;c.gpr[31]=0x08800008;unsigned reg=4;for(auto v:args)c.set_gpr(reg++,v);r.invoke_import(lib,nid,c);ck(!r.stopped(),"HLE unexpectedly stopped");return c.gpr[2];}
int main(int argc,char** argv){try{
 auto ptr=std::make_unique<Runtime>();auto& r=*ptr;renegade::install_platform_services(r);auto& c=r.cpu();auto& m=r.memory();constexpr unsigned base=0x08801000;
 ck(renegade::interrupts_enabled(r),"initial interrupts");ck(call(r,"Kernel_Library",0x092968F4,{})==1,"suspend prior");ck(!renegade::interrupts_enabled(r),"suspend state");ck(call(r,"Kernel_Library",0x092968F4,{})==0,"nested prior");call(r,"Kernel_Library",0x5F10D406,{0});ck(!renegade::interrupts_enabled(r),"nested resume stays disabled");call(r,"Kernel_Library",0x5F10D406,{1});ck(renegade::interrupts_enabled(r),"outer resume");
 ck(call(r,"ModuleMgrForUser",0xD8B73127,{0x08804000})==0x3f0,"module address");ck(call(r,"ModuleMgrForUser",0xD8B73127,{0x08c40000})==0x8002012e,"module boundary");
 ck(call(r,"scePower",0x737486F2,{333,333,166})==0,"clock set");ck(call(r,"scePower",0xFDB5BFE9,{})==333,"clock get");ck(call(r,"scePower",0x737486F2,{333,334,166})!=0,"clock reject");ck(call(r,"scePower",0xFDB5BFE9,{})==333,"clock unchanged on reject");
 for(unsigned id=2;id<=9;++id){ck(call(r,"sceUtility",0xA5DA2406,{id,base})==0,"setting query");ck(m.load32(base)<=1,"setting result");}ck(call(r,"sceUtility",0xA5DA2406,{8,0x09fffffe})!=0,"setting bad pointer");
 ck(call(r,"sceUtility",0x34B78343,{1,base,10})==0,"nickname");ck(m.read_c_string(base,10)=="Col Serra","nickname value");ck(call(r,"sceUtility",0x34B78343,{1,base,2})!=0,"nickname short buffer");
 for(unsigned id=0x300;id<=0x303;++id){ck(call(r,"sceUtility",0x2A2B3DE0,{id})==0,"codec load");ck(call(r,"sceUtility",0x2A2B3DE0,{id})!=0,"duplicate codec");ck(call(r,"sceUtility",0xE49BFE92,{id})==0,"codec unload");ck(call(r,"sceUtility",0xE49BFE92,{id})!=0,"duplicate unload");}ck(call(r,"sceUtility",0x2A2B3DE0,{0x100})!=0,"unsupported module not success");
 auto printf=[&](const std::string& fmt){str(m,base,fmt);c.gpr[4]=base;return renegade::format_psp_printf(r,c);};
 c.gpr[5]=unsigned(-123);ck(printf("%d")=="-123","signed printf");c.gpr[5]=0xff;ck(printf("%hhd")=="-1","narrow printf");c.gpr[5]=0xab;ck(printf("%08X")=="000000AB","printf padded");
 c.gpr[6]=0x76543210;c.gpr[7]=0xfedcba98;ck(printf("%llx")=="fedcba9876543210","EABI aligned 64 bit");
 auto db=std::bit_cast<std::uint64_t>(1.25);c.gpr[6]=db;c.gpr[7]=db>>32;ck(printf("%.2f")=="1.25","EABI double");
 c.gpr[29]=base+0x1000;for(unsigned a=1;a<=7;++a)c.gpr[4+a]=a;m.store32(c.gpr[29],8);m.store32(c.gpr[29]+4,9);ck(printf("%u %u %u %u %u %u %u %u %u")=="1 2 3 4 5 6 7 8 9","EABI stack spill");
 str(m,base+0x200,"abcde");c.gpr[5]=base+0x200;ck(printf("%.3s")=="abc","bounded string");c.gpr[5]=base+0x300;ck(printf("abcd%n!")=="abcd!" && m.load32(base+0x300)==4,"printf n count");
 for(const char* format:{"%999999d","%100000.3s","%.900000f","%","%Q"}){bool fail=false;try{printf(format);}catch(const Error&){fail=true;}ck(fail,"printf bad field rejection");}
 // The actual regenerated callbacks invoke synthetic callees solely in this test.
 psprecomp::register_supplemental_functions(r);unsigned called=0;
 r.register_function(0x0889609c,[](Runtime& rt,AllegrexContext& x){ck(x.gpr[4]==0x1234 && x.gpr[5]==0x5678,"callback forwards args");x.set_gpr(2,0x9abc);x.pc=x.gpr[31];},"recomp_unit_synthetic_test_callee");
 r.register_function(0x08800008,[](Runtime& rt,AllegrexContext&){rt.stop("synthetic callback returned");},"test return");
 m.store32(0x08b29ca0,0x1234);c.gpr[4]=0x5678;c.gpr[29]=base+0x2000;c.gpr[31]=0x08800008;r.run(0x08896118,100);
 ck(r.stop_reason()=="synthetic callback returned","callback return");ck(c.gpr[29]==base+0x2000 && c.gpr[2]==0x9abc,"callback stack and return value");
 sort_callback_called=0;
 r.register_function(0x08A2E320,[](Runtime& rt,AllegrexContext& x){++sort_callback_called;ck(x.gpr[4]==0xfffffff6u && x.gpr[5]==5u,"sort callback forwards z");ck(x.gpr[6]==0xfffffffcu && x.gpr[7]==7u,"sort callback forwards y");ck(x.gpr[8]==0xfffffffdu && x.gpr[9]==0xffff8001u,"sort callback forwards x");x.set_gpr(2,0);x.pc=x.gpr[31];},"recomp_unit_synthetic_sort_callee");
 r.register_function(0x0880000c,[](Runtime& rt,AllegrexContext&){rt.stop("sort callback returned true");},"test sort return");
 auto put16=[&](unsigned a,std::int16_t v){m.store16(a,static_cast<std::uint16_t>(v));};
 unsigned lhs=base+0x5000,rhs=base+0x5100,sp=base+0x6000;
 put16(lhs+16,-4);put16(lhs+18,7);put16(lhs+20,-10);put16(rhs+16,-3);put16(rhs+18,-32767);put16(rhs+20,5);
 c.gpr[4]=lhs;c.gpr[5]=rhs;c.gpr[29]=sp;c.gpr[31]=0x0880000c;r.run(0x08A2E2E4,100);
 ck(r.stop_reason()=="sort callback returned true","sort callback return dispatch");ck(c.gpr[29]==sp && c.gpr[31]==0x0880000c,"sort callback stack and ra");ck(c.gpr[2]==1 && sort_callback_called==1,"sort callback result true");
 r.stop("");
 r.register_function(0x08800010,[](Runtime& rt,AllegrexContext&){rt.stop("sort continuation returned false");},"test sort continuation");
 m.store32(sp,0x08800010);c.gpr[29]=sp;c.gpr[31]=0xeeeeeeee;c.gpr[2]=2;r.run(0x08A2E310,100);
 ck(r.stop_reason()=="sort continuation returned false","sort continuation dispatch");ck(c.gpr[29]==sp+16 && c.gpr[31]==0x08800010 && c.gpr[2]==0,"sort continuation result false");
 // Asset-dependent header parser coverage does not treat movies as 3D gameplay.
 if(argc>1){auto q=std::make_unique<Runtime>();auto& t=*q;t.set_game_root(argv[1]);renegade::install_psmf_services(t);auto& mm=t.memory();str(mm,base,"disc0:/PSP_GAME/USRDIR/MODULE/PSMF.PRX");
 auto uid=call(t,"ModuleMgrForUser",0x977DE386,{base,0,0});ck(uid==0x1000,"known module identity");ck(call(t,"ModuleMgrForUser",0x50F0C1EC,{uid,0,0,base+0x400})==uid,"known module start");ck(mm.load32(base+0x400)==0,"module status");
 unsigned movies=0;for(auto& item:std::filesystem::recursive_directory_iterator(argv[1]))if(item.path().extension()==".PMF"){
  std::array<unsigned char,2048> data;std::ifstream f(item.path(),std::ios::binary);f.read(reinterpret_cast<char*>(data.data()),data.size());ck(f.gcount()==2048,"real movie header length");for(unsigned i=0;i<data.size();++i)mm.store8(base+0x1000+i,data[i]);
  ck(call(t,"scePsmf",0xc22c8327,{base+0x100,base+0x1000})==0,"real header parsed");unsigned video=call(t,"scePsmf",0x68d42328,{base+0x100,0}),audio=call(t,"scePsmf",0x68d42328,{base+0x100,15});ck(video==1,"real video stream");ck(video+audio==unsigned(data[0x80])*256+data[0x81],"all declared streams counted");++movies;
 }
 ck(movies==23,"all supplied movie headers including ICON1.PMF");
 mm.store8(base+0x1000,'X');ck(call(t,"scePsmf",0xc22c8327,{base+0x100,base+0x1000})!=0,"corrupt header rejected");ck(call(t,"scePsmf",0xc22c8327,{0x09fffff0,base+0x1000})!=0,"header output bounds");
 ck(call(t,"ModuleMgrForUser",0xd1ff982a,{uid,0,0,0})==0,"module stopped");ck(call(t,"ModuleMgrForUser",0x2e0911aa,{uid})==0,"module unloaded");ck(call(t,"scePsmf",0x68d42328,{base+0x100,0})!=0,"unload invalidates header state");
 }
 std::cout<<"PASS "<<checks<<" platform/printf/callback/PSMF checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<"\n";return 1;}}
