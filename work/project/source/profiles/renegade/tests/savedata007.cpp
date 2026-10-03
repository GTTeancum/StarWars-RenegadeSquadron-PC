
#include "psprecomp/runtime.hpp"
#include "vcs_profile.hpp"
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <memory>
#include <string>
namespace fs=std::filesystem;
int main() {
 unsigned checks=0,failures=0;
 auto check=[&](bool ok,const char* name){++checks;if(!ok){++failures;std::cerr<<"FAIL: "<<name<<"\n";}};
 const auto root=fs::temp_directory_path()/("renegade-save-test007-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
 fs::create_directories(root);
 struct Cleanup {fs::path p;~Cleanup(){std::error_code e;fs::remove_all(p,e);}} cleanup{root};
 auto heap=std::make_unique<psprecomp::Runtime>(); auto& r=*heap;auto& m=r.memory();
 r.set_game_root(root);vcs::install_profile(r,0x08C40000u);
 constexpr unsigned p=0x08820000u,data=0x08830000u,aux=0x08831000u,out=0x08832000u;
 const auto dir=root/"PSP/SAVEDATA/ULUS10292TEST";
 auto put=[&](const fs::path& f,const std::string& s){fs::create_directories(f.parent_path());std::ofstream(f,std::ios::binary|std::ios::trunc)<<s;};
 auto read=[&](const fs::path& f){std::ifstream in(f,std::ios::binary);return std::string(std::istreambuf_iterator<char>(in),{});};
 auto str=[&](unsigned a,const std::string& s){for(unsigned i=0;i<s.size();++i)m.store8(a+i,s[i]);m.store8(a+s.size(),0);};
 auto prepare=[&](unsigned mode=1){
  m.zero(p,0x600);m.store32(p,0x600);m.store32(p+0x30,mode);
  str(p+0x3c,"ULUS10292");str(p+0x4c,"TEST");str(p+0x64,"DATA.BIN");
  m.store32(p+0x74,data);m.store32(p+0x78,32);m.store32(p+0x7c,4);str(data,"NEW!");
  str(aux,"ICON");put(dir/"DATA.BIN","OLD!");put(dir/"ICON0.PNG","OLDICON");
 };
 auto call=[&](unsigned nid,unsigned arg=0){
  auto& c=r.cpu();c={};c.pc=0x08801000;c.gpr[31]=0x08801008;c.gpr[4]=arg;
  r.invoke_import("sceUtility",nid,c);
  if(r.stopped())throw std::runtime_error("Production savedata import stopped: "+r.stop_reason());
  return c.gpr[2];
 };
 auto operation=[&]{
  check(call(0x50C4CD57,p)==0,"init accepted valid parameter");
  check(call(0x8874DBE0)==1,"lifecycle Init");
  check(call(0x8874DBE0)==2,"lifecycle Visible");
  check(call(0xD4B95FFB,1)==0,"utility update");
  check(call(0x8874DBE0)==3,"lifecycle Quit");
  auto result=m.load32(p+0x1c);
  check(call(0x9790B33C)==0,"shutdown");
  check(call(0x8874DBE0)==4,"lifecycle Finished");
  check(call(0x8874DBE0)==0,"lifecycle reset");
  return result;
 };
 try {
  for(unsigned offset:{0x584u,0x594u,0x5a4u,0x5b4u}) {
   prepare();m.store32(p+offset,0xDEADBEEFu);m.store32(p+offset+4,8);m.store32(p+offset+8,8);
   check(operation()!=0,"bad auxiliary pointer rejected");
   check(read(dir/"DATA.BIN")=="OLD!","bad auxiliary pointer preserved original DATA.BIN");
   check(read(dir/"ICON0.PNG")=="OLDICON","bad auxiliary pointer preserved original ICON0");
  }
  prepare();m.store32(p+0x594,0);m.store32(p+0x598,4);m.store32(p+0x59c,4);
  check(operation()!=0,"null nonempty auxiliary rejected");
  check(read(dir/"DATA.BIN")=="OLD!","null nonempty auxiliary preserved original");
  prepare();m.store32(p+0x584,aux);m.store32(p+0x588,2);m.store32(p+0x58c,4);
  check(operation()!=0,"auxiliary capacity overflow rejected");
  check(read(dir/"DATA.BIN")=="OLD!","capacity overflow preserved original");
  prepare();m.store32(p+0x7c,0);m.store32(p+0x74,0);
  check(operation()==0,"zero-length main save accepted");
  check(fs::is_regular_file(dir/"DATA.BIN")&&fs::file_size(dir/"DATA.BIN")==0,"zero-length main replaces old bytes");
  check(read(dir/"ICON0.PNG")=="OLDICON","omitted auxiliary preserved");
  prepare();m.store32(p+0x584,aux);m.store32(p+0x588,4);m.store32(p+0x58c,4);
  check(operation()==0,"valid main and icon save");
  check(read(dir/"DATA.BIN")=="NEW!"&&read(dir/"ICON0.PNG")=="ICON","published main and icon bytes");
  prepare(18);m.store32(p+0x594,0xDEADBEEFu);m.store32(p+0x598,4);m.store32(p+0x59c,4);
  check(operation()==0,"raw save ignores unused auxiliary descriptors");
  check(read(dir/"DATA.BIN")=="NEW!"&&read(dir/"ICON0.PNG")=="OLDICON","raw save preserved other files");
  for(unsigned bad:{1u,2u}) {
   prepare(8);m.store32(p+0x5d0,out);m.store32(p+0x5d4,out+64);m.store32(p+0x5d8,out+160);
   m.store32(p+0x5d0+4*bad,0xDEADBEEFu);
   for(unsigned i=0;i<192;++i)m.store8(out+i,0xA5);
   check(operation()!=0,"invalid later sizes output rejected");
   bool unchanged=true;for(unsigned i=0;i<192;++i)unchanged&=m.load8(out+i)==0xA5;
   check(unchanged,"invalid later sizes output preserved every earlier output");
  }
  prepare(8);m.store32(p+0x5d0,out);m.store32(p+0x5d4,out+64);m.store32(p+0x5d8,out+160);
  check(operation()==0,"valid sizes query");
  check(m.load32(out)==32768,"cluster-size output correct");
 } catch(const std::exception& e) {++failures;std::cerr<<"EXCEPTION: "<<e.what()<<"\n";}
 std::cout<<"production_savedata_checks="<<checks<<" failures="<<failures<<"\n";
 return failures?1:0;
}
