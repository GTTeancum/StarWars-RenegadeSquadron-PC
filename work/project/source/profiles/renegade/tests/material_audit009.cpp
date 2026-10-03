#include "material_audit009.hpp"
#include <array>
#include <iostream>
#include <filesystem>
#include <fstream>
#include <sstream>
int main(){using namespace renegade::materials009;
 unsigned checks=0,failed=0;auto ck=[&](bool b){++checks;if(!b)++failed;};
 Collector a;std::array<std::uint32_t,256> c{};
 a.observe(10,c,0);ck(a.rows().empty());
 c[0x12]=(3u<<5)|(7u<<2)|3u;c[0x17]=1;c[0x5E]=1;c[0x1E]=1;c[0x18]=1;
 const auto before=c;a.observe(10,c,3);a.observe(8,c,6);a.observe(12,c,3);
 ck(c==before);ck(a.rows().size()==1);const auto& row=a.rows().begin()->second;
 ck(row.draws==3);ck(row.vertices==12);ck(row.first==8&&row.last==12);
 const auto& key=a.rows().begin()->first;ck(key.light_mask==1);ck(key.lightmode==1);
 for(unsigned i=0;i<4;++i){auto d=c;d[0x12]=(d[0x12]&~96u)|(i<<5);a.observe(20,d,3);}
 ck(a.rows().size()==4);
 c[0x12]|=1u<<23;a.observe(21,c,6);c[0xD3]=1;a.observe(22,c,6);ck(a.rows().size()==6);
 Collector bounded;for(unsigned i=0;i<4100;++i){c[0x57]=i;bounded.observe(i,c,1);}
 ck(bounded.rows().size()==4096);ck(bounded.dropped()==4);
 std::filesystem::path out=std::filesystem::temp_directory_path()/"renegade-material-test009.json";
 a.write(out);std::ifstream f(out);std::stringstream ss;ss<<f.rdbuf();auto text=ss.str();f.close();
 ck(text.find("\"raster_modified\":false")!=std::string::npos);
 ck(text.find("\"non_through_non_clear_draws\":7")!=std::string::npos);
 ck(text.find("\"world_with_normals\":6")!=std::string::npos);
 ck(text.find("\"draws\":9")!=std::string::npos);
 std::filesystem::remove(out);std::cout<<"material_audit009_checks="<<checks<<" failures="<<failed<<"\n";return failed?1:0;
}
