#include "psprecomp/runtime.hpp"
#include "stdio_eabi.hpp"
#include <memory>
#include <unordered_map>
#include <set>
#include <iostream>
#include <cstring>
namespace renegade {
namespace {
struct PlatformState{bool interrupts{true};unsigned pll{222},cpu{222},bus{111};std::set<unsigned> avmodules;};
std::unordered_map<psprecomp::Runtime*,std::weak_ptr<PlatformState>> states;
}
bool interrupts_enabled(psprecomp::Runtime& r){auto found=states.find(&r);if(found==states.end())return true;auto s=found->second.lock();return !s || s->interrupts;}
void install_platform_services(psprecomp::Runtime& rt){
 using R=psprecomp::Runtime;using C=psprecomp::AllegrexContext;auto s=std::make_shared<PlatformState>();states[&rt]=s;
 auto bind=[&](const char* l,unsigned id,const char* name,R::HleFunction f){rt.nids().add(l,id,name);rt.register_hle(l,id,std::move(f));};
 bind("ModuleMgrForUser",0xD8B73127,"sceKernelGetModuleIdByAddress",[](R&,C& c){c.set_gpr(2,c.gpr[4]>=0x08804000 && c.gpr[4]<0x08c40000?0x3f0:0x8002012e);});
 bind("ModuleMgrForUser",0xF0A26395,"sceKernelGetModuleId",[](R&,C& c){c.set_gpr(2,0x3f0);});
 bind("Kernel_Library",0x092968F4,"sceKernelCpuSuspendIntr",[s](R&,C& c){const bool old=s->interrupts;s->interrupts=false;c.set_gpr(2,old?1:0);});
 for(unsigned id:{0x5F10D406u,0x3B84732Du})bind("Kernel_Library",id,"sceKernelCpuResumeIntr",[s](R&,C& c){s->interrupts=(c.gpr[4]&1)!=0;c.set_gpr(2,0);});
 bind("Kernel_Library",0xB55249D2,"sceKernelIsCpuIntrEnable",[s](R&,C& c){c.set_gpr(2,s->interrupts?1:0);});
 bind("Kernel_Library",0x47A0B729,"sceKernelIsCpuIntrSuspended",[](R&,C& c){c.set_gpr(2,c.gpr[4]==0?1:0);});
 bind("SysMemUserForUser",0x13A5ABEF,"sceKernelPrintf",[](R& r,C& c){auto text=format_psp_printf(r,c);std::cerr<<"[psp] "<<text;c.set_gpr(2,static_cast<unsigned>(text.size()));});
 for(auto [id,fd]:{std::pair{0x172D316Eu,0u},std::pair{0xA6BAB2E9u,1u},std::pair{0xF78BA90Au,2u}})bind("StdioForUser",id,"sceKernelStandardDescriptor",[fd](R&,C& c){c.set_gpr(2,fd);});
 bind("sceUtility",0xA5DA2406,"sceUtilityGetSystemParamInt",[](R& r,C& c){const auto id=c.gpr[4],ptr=c.gpr[5];if(id<2 || id>9){c.set_gpr(2,0x80110103);return;}if(!r.memory().contains(ptr,4)){c.set_gpr(2,0x800200d3);return;}const unsigned values[]={0,0,0,1,1,0,0,0,1,1};r.memory().store32(ptr,values[id]);c.set_gpr(2,0);});
 bind("sceUtility",0x34B78343,"sceUtilityGetSystemParamString",[](R& r,C& c){if(c.gpr[4]!=1){c.set_gpr(2,0x80110103);return;}constexpr char name[]="Col Serra";if(c.gpr[6]<sizeof(name)){c.set_gpr(2,0x80110102);return;}if(!r.memory().contains(c.gpr[5],sizeof(name))){c.set_gpr(2,0x800200d3);return;}for(unsigned i=0;i<sizeof(name);++i)r.memory().store8(c.gpr[5]+i,name[i]);c.set_gpr(2,0);});
 auto load=[s](R&,C& c){unsigned id=c.gpr[4];if(id<=3)id+=0x300;if(id<0x300 || id>0x303){c.set_gpr(2,0x80111101);return;}if(!s->avmodules.insert(id).second){c.set_gpr(2,0x80111102);return;}std::cerr<<"[module] host codec utility loaded 0x"<<std::hex<<id<<std::dec<<"\n";c.set_gpr(2,0);};
 auto unload=[s](R&,C& c){unsigned id=c.gpr[4];if(id<=3)id+=0x300;c.set_gpr(2,s->avmodules.erase(id)?0:0x80111103);};
 bind("sceUtility",0x2A2B3DE0,"sceUtilityLoadModule",load);bind("sceUtility",0xE49BFE92,"sceUtilityUnloadModule",unload);
 bind("sceUtility",0xC629AF26,"sceUtilityLoadAvModule",load);bind("sceUtility",0xF7D8D092,"sceUtilityUnloadAvModule",unload);
 auto clocks=[s](R&,C& c){unsigned pll=c.gpr[4],cpu=c.gpr[5],bus=c.gpr[6];if(pll<19 || pll>333 || cpu<1 || cpu>333 || cpu>pll || bus<1 || bus>166 || bus>pll){c.set_gpr(2,0x80000107);return;}s->pll=pll;s->cpu=cpu;s->bus=bus;c.set_gpr(2,0);};
 bind("scePower",0x737486F2,"scePowerSetClockFrequency",clocks);bind("scePower",0xEBD177D6,"scePowerSetClockFrequency350",clocks);
 for(unsigned id:{0xFDB5BFE9u,0xFEE03A2Fu})bind("scePower",id,"scePowerGetCpuClockFrequencyInt",[s](R&,C& c){c.set_gpr(2,s->cpu);});
 for(unsigned id:{0xBD681969u,0x478FE6F5u})bind("scePower",id,"scePowerGetBusClockFrequencyInt",[s](R&,C& c){c.set_gpr(2,s->bus);});
 bind("scePower",0xB1A52C83,"scePowerGetCpuClockFrequencyFloat",[s](R&,C& c){c.fpr[0]=static_cast<float>(s->cpu);});
 bind("scePower",0x9BADB3EB,"scePowerGetBusClockFrequencyFloat",[s](R&,C& c){c.fpr[0]=static_cast<float>(s->bus);});
}
}
