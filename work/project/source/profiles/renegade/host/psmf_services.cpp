// Renegade host implementation of the two PSMF header APIs used by ULUS10292.
// Original PRX bytes are identified but never executed or represented as executed.
#include "psprecomp/runtime.hpp"
#include "psprecomp/sha256.hpp"
#include <array>
#include <algorithm>
#include <filesystem>
#include <iostream>
#include <memory>
#include <unordered_map>
namespace renegade {
namespace {
constexpr unsigned kInvalid=0x80615001u,kVersion=0x80615002u,kBadAddress=0x800200d3u;
struct Header {unsigned data{},version{},offset{},size{},total{};std::array<unsigned,3> counts{};};
struct MediaState {unsigned next{0x1000};std::unordered_map<unsigned,bool> modules;std::unordered_map<unsigned,Header> headers;};
unsigned be32(psprecomp::GuestMemory& m,unsigned p){return unsigned(m.load8(p))<<24|unsigned(m.load8(p+1))<<16|unsigned(m.load8(p+2))<<8|m.load8(p+3);}
Header read_header(psprecomp::GuestMemory& m,unsigned p){
 if(!m.contains(p,2048))throw psprecomp::Error("PSMF header crosses guest memory boundary");
 if(m.load32(p)!=0x464d5350u)throw psprecomp::Error("Invalid PSMF magic");
 Header h;h.data=p;auto raw=m.load32(p+4);
 switch(raw){case 0x32313030:h.version=0x0f;break;case 0x33313030:h.version=0x1f;break;case 0x34313030:h.version=0x2f;break;case 0x35313030:h.version=0x3f;break;default:throw psprecomp::Error("Unsupported PSMF version");}
 h.offset=be32(m,p+8);h.size=be32(m,p+12);h.total=unsigned(m.load8(p+0x80))*256+m.load8(p+0x81);
 if(h.offset<2048 || (h.offset&2047) || h.total>(2048-0x82)/16)throw psprecomp::Error("Invalid PSMF stream directory");
 for(unsigned i=0;i<h.total;++i){auto d=p+0x82+16*i;unsigned id=m.load8(d),sub=m.load8(d+1);
  if((id&0xf0)==0xe0)++h.counts[0];else if(id==0xbd && sub<0x10)++h.counts[1];else if(id==0xbd && sub>=0x10 && sub<0x20)++h.counts[2];
  else throw psprecomp::Error("Unsupported PSMF stream descriptor");
 }
 return h;
}
}
void install_psmf_services(psprecomp::Runtime& rt){
 using R=psprecomp::Runtime;using C=psprecomp::AllegrexContext;auto s=std::make_shared<MediaState>();
 auto bind=[&](const char* lib,unsigned id,const char* name,R::HleFunction f){rt.nids().add(lib,id,name);rt.register_hle(lib,id,std::move(f));};
 bind("ModuleMgrForUser",0x977DE386,"sceKernelLoadModule",[s](R& r,C& c){
  std::string path=r.memory().read_c_string(c.gpr[4],1024);auto native=r.translate_path(path);
  std::cerr<<"[module] requested path="<<path<<" native="<<native<<"\n";
  if(!std::filesystem::is_regular_file(native)){c.set_gpr(2,0x80010002);return;}
  if(native.filename()!="PSMF.PRX" || std::filesystem::file_size(native)!=static_cast<std::uintmax_t>(7440) || psprecomp::sha256_file(native)!="83dd649650fce7a6b6d8b0e02d613f4621978486d5718a4b9b26f0250f793134"){
   r.stop("Unsupported or mismatched guest module: "+path);c.set_gpr(2,0x80020148);return;
  }
  auto uid=s->next++;s->modules.emplace(uid,false);c.set_gpr(2,uid);std::cerr<<"[module] identified PSMF.PRX: host header API implementation; guest PRX not executed; uid="<<uid<<"\n";
 });
 bind("ModuleMgrForUser",0xB7F46618,"sceKernelLoadModuleByID",[](R& r,C& c){c.set_gpr(2,0x80020148);r.stop("Module-by-descriptor is not implemented; refusing a fictitious module load");});
 auto lifecycle=[s](bool start){return [s,start](R& r,C& c){auto it=s->modules.find(c.gpr[4]);if(it==s->modules.end()){c.set_gpr(2,0x8002012e);return;}
  if(c.gpr[7] && !r.memory().contains(c.gpr[7],4)){c.set_gpr(2,kBadAddress);return;}
  if(c.gpr[5] && !r.memory().contains(c.gpr[6],c.gpr[5])){c.set_gpr(2,kBadAddress);return;}
  it->second=start;if(c.gpr[7])r.memory().store32(c.gpr[7],0);c.set_gpr(2,start?it->first:0);
 };};
 bind("ModuleMgrForUser",0x50F0C1EC,"sceKernelStartModule",lifecycle(true));bind("ModuleMgrForUser",0xD1FF982A,"sceKernelStopModule",lifecycle(false));
 bind("ModuleMgrForUser",0x2E0911AA,"sceKernelUnloadModule",[s](R&,C& c){auto i=s->modules.find(c.gpr[4]);if(i==s->modules.end()){c.set_gpr(2,0x8002012e);return;}if(i->second){c.set_gpr(2,0x8002013b);return;}s->modules.erase(i);s->headers.clear();c.set_gpr(2,0);});
 bind("scePsmf",0xC22C8327,"scePsmfSetPsmf",[s](R& r,C& c){
  const unsigned out=c.gpr[4],data=c.gpr[5];if(!r.memory().contains(out,32)||!r.memory().contains(data,2048)){c.set_gpr(2,kBadAddress);return;}
  bool active=false;for(auto& [id,started]:s->modules)active|=started;if(!active){c.set_gpr(2,0x8002012e);return;}
  Header h;try{h=read_header(r.memory(),data);}catch(const psprecomp::Error& e){std::cerr<<"[psmf] "<<e.what()<<"\n";c.set_gpr(2,kInvalid);return;}
  // Context owns no game-state variables. It records only the parsed media header.
  const unsigned values[]={h.version,2048,data,h.size,h.offset,0,0,0};for(unsigned i=0;i<8;++i)r.memory().store32(out+4*i,values[i]);s->headers[data]=h;c.set_gpr(2,0);
  std::cerr<<"[psmf] header=0x"<<std::hex<<data<<std::dec<<" AVC="<<h.counts[0]<<" ATRAC="<<h.counts[1]<<" PCM="<<h.counts[2]<<"\n";
 });
 bind("scePsmf",0x68D42328,"scePsmfGetNumberOfSpecificStreams",[s](R& r,C& c){if(!r.memory().contains(c.gpr[4],32)){c.set_gpr(2,kBadAddress);return;}auto it=s->headers.find(r.memory().load32(c.gpr[4]+8));if(it==s->headers.end()){c.set_gpr(2,kInvalid);return;}const auto type=c.gpr[5];c.set_gpr(2,type<3?it->second.counts[type]:type==15?it->second.counts[1]+it->second.counts[2]:0);});
}
}
