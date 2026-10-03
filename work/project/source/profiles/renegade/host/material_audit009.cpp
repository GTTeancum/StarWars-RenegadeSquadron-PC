#include "material_audit009.hpp"
#include <cstdlib>
#include <fstream>
#include <string>
#include <stdexcept>
#include <mutex>
#include <memory>
namespace renegade::materials009 {
namespace {
std::mutex mutex;
std::unique_ptr<Collector> collector;
std::filesystem::path destination;
std::uint64_t(*frame_source)()=nullptr;
std::uint64_t start=0;
}
void Collector::observe(std::uint64_t frame,const std::array<std::uint32_t,256>& c,std::uint32_t n) {
 if(!n)return;
 Key key{c[0x12]&0xFFFFFFu,c[0x17]&1u,c[0x5E]&1u,c[0x1E]&1u,c[0xD3]&1u,
         c[0x53]&7u,c[0x57]&0xFFFFFFu,0};
 for(unsigned i=0;i<4;++i)key.light_mask|=(c[0x18+i]&1u)<<i;
 auto it=rows_.find(key);
 if(it==rows_.end()){
  if(rows_.size()>=4096){++dropped_;return;}
  it=rows_.emplace(key,Counts{0,0,frame,frame}).first;
 }
 auto& row=it->second;++row.draws;row.vertices+=n;
 row.first=std::min(row.first,frame);row.last=std::max(row.last,frame);
}
void Collector::write(const std::filesystem::path& path)const {
 if(path.empty())throw std::invalid_argument("Empty material report path");
 std::filesystem::create_directories(path.parent_path().empty()?std::filesystem::path("."):path.parent_path());
 auto temp=path;temp+=".tmp";
 std::ofstream f(temp,std::ios::trunc);if(!f)throw std::runtime_error("Cannot create material audit");
 std::uint64_t total=0,world=0,normals=0,lit=0,separate=0,textured=0,lit_normals=0;
 for(auto& [k,c]:rows_){total+=c.draws;if(!(k.vtype&(1u<<23))&&!k.clear){
  world+=c.draws;if((k.vtype>>5)&3)normals+=c.draws;
  if(k.lighting){lit+=c.draws;if((k.vtype>>5)&3)lit_normals+=c.draws;if(k.lightmode)separate+=c.draws;}
  if(k.texture)textured+=c.draws;
 }}
 f<<"{\n\"format\":\"renegade-material-audit009\",\"raster_modified\":false,"
  <<"\"draws\":"<<total<<",\"non_through_non_clear_draws\":"<<world
  <<",\"world_with_normals\":"<<normals<<",\"world_lighting_enabled\":"<<lit
  <<",\"world_lit_with_normals\":"<<lit_normals
  <<",\"world_lit_separate_specular\":"<<separate<<",\"world_textured\":"<<textured
  <<",\"dropped_unique_state_draws\":"<<dropped_<<",\n\"states\":[\n";
 bool first=true;
 for(auto& [k,c]:rows_){if(!first)f<<",\n";first=false;
  f<<"{\"vertex_type\":"<<k.vtype<<",\"normal_format\":"<<((k.vtype>>5)&3)
   <<",\"color_format\":"<<((k.vtype>>2)&7)<<",\"through\":"<<((k.vtype>>23)&1)
   <<",\"lighting\":"<<k.lighting<<",\"lightmode\":"<<k.lightmode
   <<",\"textured\":"<<k.texture<<",\"clear\":"<<k.clear<<",\"material_update\":"<<k.material_update
   <<",\"specular_rgb\":"<<k.specular_rgb<<",\"light_mask\":"<<k.light_mask
   <<",\"draws\":"<<c.draws<<",\"submitted_vertices\":"<<c.vertices
   <<",\"first_vblank\":"<<c.first<<",\"last_vblank\":"<<c.last<<"}";
 }
 f<<"\n]}\n";f.flush();if(!f)throw std::runtime_error("Material report write failed");f.close();
 std::filesystem::rename(temp,path);
}
void begin_from_environment(std::uint64_t(*frame)()) {
 std::lock_guard lock(mutex);collector.reset();destination.clear();frame_source=frame;start=0;
 const char* path=std::getenv("RENEGADE_MATERIAL_AUDIT");if(!path||!*path)return;
 if(!frame)throw std::invalid_argument("Material report requires frame source");
 if(const char* n=std::getenv("RENEGADE_MATERIAL_AUDIT_START")){
  std::string s(n);std::size_t used=0;
  if(s.empty()||s[0]=='-')throw std::invalid_argument("Invalid material audit start");
  start=std::stoull(s,&used);if(used!=s.size())throw std::invalid_argument("Invalid material audit start");
 }
 destination=path;collector=std::make_unique<Collector>();
}
void observe(const std::array<std::uint32_t,256>& c,std::uint32_t count) {
 if(!collector)return; // Single guest-render thread, configured before execution.
 const auto frame=frame_source();if(frame<start)return;
 std::lock_guard lock(mutex);collector->observe(frame,c,count);
}
void finish(){std::lock_guard lock(mutex);if(collector)collector->write(destination);}
}
