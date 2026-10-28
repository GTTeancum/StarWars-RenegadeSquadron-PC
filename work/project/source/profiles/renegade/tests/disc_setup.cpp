#include "disc_setup.hpp"
#include <iostream>
int main(int argc,char** argv) {
 try {
  if(argc!=2)throw std::runtime_error("Usage: renegade_disc_setup_test installation-directory");
  const std::filesystem::path root=argv[1];
  renegade::disc_setup::prepare(root);
  if(!renegade::disc_setup::complete(root/"data"))throw std::runtime_error("Extraction incomplete");
  const auto boot=root/"data/PSP_GAME/SYSDIR/BOOT.BIN";
  const auto modified=std::filesystem::last_write_time(boot);
  renegade::disc_setup::prepare(root);
  if(modified!=std::filesystem::last_write_time(boot))throw std::runtime_error("Second launch overwrote extracted game data");
  std::cout<<"PASS: ISO extraction, game identity, repeat launch preserves files\n";
  return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}
}
