#include "../host/atomic_status011.hpp"
#include <fstream>
#include <iostream>
#include <string>
#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#endif
int main(){
 namespace fs=std::filesystem;using namespace std::chrono_literals;
 unsigned checks=0,fail=0;auto ck=[&](bool v,const char* why){++checks;if(!v){++fail;std::cerr<<"FAIL "<<why<<'\n';}};
 const auto dir=fs::temp_directory_path()/("renegade-status011-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
 fs::create_directory(dir);const auto target=dir/"status.json",temp=dir/"status.json.tmp";
 auto write=[](const fs::path& p,const char* s){std::ofstream f(p);f<<s;if(!f)throw std::runtime_error("write fixture");};
 auto read=[](const fs::path& p){std::ifstream f(p);return std::string(std::istreambuf_iterator<char>(f),{});};
 try{
  write(target,"old complete status");write(temp,"new complete status");
#ifdef _WIN32
  // Match a normal polling reader that does not grant FILE_SHARE_DELETE.
  HANDLE held=CreateFileW(target.c_str(),GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,OPEN_EXISTING,0,nullptr);
  ck(held!=INVALID_HANDLE_VALUE,"open competing reader");
  if(held==INVALID_HANDLE_VALUE)throw std::runtime_error("reader fixture");
  std::error_code ec;fs::rename(temp,target,ec);
  ck(bool(ec),"baseline rename reproduces Windows sharing failure");
  ck(read(target)=="old complete status"&&fs::exists(temp),"failed baseline retains complete old and staged status");
  std::thread release([held]{std::this_thread::sleep_for(80ms);CloseHandle(held);});
  bool published=true;try{renegade::diagnostic011::publish(temp,target,1000ms);}catch(...){published=false;}
  release.join();ck(published,"publication succeeds when competing reader releases");
#else
  renegade::diagnostic011::publish(temp,target);
#endif
  ck(read(target)=="new complete status"&&!fs::exists(temp),"atomic replacement publishes complete new status");
#ifdef _WIN32
  write(temp,"later complete status");
  held=CreateFileW(target.c_str(),GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,OPEN_EXISTING,0,nullptr);
  ck(held!=INVALID_HANDLE_VALUE,"open persistent competing reader");
  if(held==INVALID_HANDLE_VALUE)throw std::runtime_error("reader fixture");
  bool rejected=false;const auto before=std::chrono::steady_clock::now();
  try{renegade::diagnostic011::publish(temp,target,30ms);}catch(const fs::filesystem_error&){rejected=true;}
  const auto elapsed=std::chrono::steady_clock::now()-before;CloseHandle(held);
  ck(rejected&&elapsed<2s,"persistent denial fails within bounded time");
  ck(read(target)=="new complete status"&&read(temp)=="later complete status","timeout loses neither status");
  renegade::diagnostic011::publish(temp,target);ck(read(target)=="later complete status","retry after release succeeds");
#endif
  bool missing=false;try{renegade::diagnostic011::publish(dir/"missing",target);}catch(const fs::filesystem_error&){missing=true;}
  ck(missing&&fs::exists(target),"missing staged source fails without deleting current status");
 }catch(const std::exception& e){++fail;std::cerr<<e.what()<<'\n';}
 fs::remove(temp);fs::remove(target);fs::remove(dir);
 std::cout<<"diagnostic011_checks="<<checks<<" failures="<<fail<<'\n';return fail?1:0;
}
