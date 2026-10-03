// Optional controller-only bounded stepping. No guest-state mutation or save-state injection.
#include "diagnostic_control.hpp"
#include "atomic_status011.hpp"
#include "diagnostic_gpu_capture.hpp"
#include "display_window.hpp"
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <thread>
#include <chrono>
#include <iostream>
namespace renegade { namespace {
struct State {std::filesystem::path dir;std::uint64_t sequence{},until{};std::uint32_t buttons{};std::uint8_t x{128},y{128};bool enabled{};};
State& state(){static State s=[] {State a;const char* d=std::getenv("RENEGADE_CONTROL_DIRECTORY");if(!d||!*d)return a;a.dir=d;std::filesystem::create_directories(a.dir);a.enabled=true;if(const char* n=std::getenv("RENEGADE_CONTROL_START")){std::size_t used;std::string t=n;a.until=std::stoull(t,&used,0);if(used!=t.size())throw psprecomp::Error("Bad control-start value");}return a;}();return s;}
void status(State& s,std::uint64_t frame,const std::string& image,bool paused,const diagnostic104::GpuCapture& gpu){auto p=s.dir/"status.json";auto temp=p;temp+=".tmp";{std::ofstream f(temp);f<<"{\"sequence\":"<<s.sequence<<",\"vblank\":"<<frame<<",\"until\":"<<s.until<<",\"paused\":"<<(paused?"true":"false")<<",\"frame\":\""<<image<<"\",\"gpu_capture\":"<<(gpu.captured?"true":"false")<<",\"gpu_source_vblank\":"<<gpu.source_vblank<<",\"gpu_width\":"<<gpu.width<<",\"gpu_height\":"<<gpu.height<<",\"gpu_frame\":\""<<gpu.frame<<"\",\"gpu_fxaa_frame\":\""<<gpu.fxaa_frame<<"\"}\n";if(!f)throw psprecomp::Error("Cannot save controller-step status");}diagnostic011::publish(temp,p);}
}
std::uint32_t control_buttons(std::uint64_t frame){auto& s=state();return s.enabled && frame<s.until?s.buttons:0;}
bool control_analog(std::uint64_t frame,std::uint8_t& x,std::uint8_t& y){auto& s=state();if(!s.enabled || !s.sequence || frame>=s.until)return false;x=s.x;y=s.y;return true;}
void control_vblank(psprecomp::Runtime& r,const vcs::FramebufferDescription& desc,std::uint64_t frame){auto& s=state();if(!s.enabled || frame<s.until)return;
 auto filename="pause_"+std::to_string(s.sequence)+"_vblank_"+std::to_string(frame)+".ppm";
 vcs::write_framebuffer_ppm(s.dir/filename,desc,vcs::decode_framebuffer_rgb(r.memory(),desc));
 const auto* fxaa=std::getenv("RENEGADE_FXAA");
 const auto gpu=diagnostic104::capture_gpu_frame(s.dir,std::filesystem::path(filename).stem().string(),frame,desc.address,vcs::ge_gpu_backend_report(),vcs::ge_gpu_backend_game_frame_rgba(),fxaa&&std::string(fxaa)=="1");
 status(s,frame,filename,true,gpu);
 std::cerr<<"[controller-step] paused vblank="<<frame<<" sequence="<<s.sequence<<"\n";
 for(;;){
  // Host pause is not a guest clock step. Keep the native toolbar responsive.
  if(vcs::display_window_close_requested()){r.stop("Display window closed by the user");return;}
  {std::ifstream in(s.dir/"command.txt");if(in){std::string a,b,c,d,e,junk;if((in>>a>>b>>c>>d>>e)&&!(in>>junk)){
   auto parse=[](const std::string& text){if(text.empty()||text[0]=='-')throw psprecomp::Error("Negative controller command");std::size_t n;auto v=std::stoull(text,&n,0);if(n!=text.size())throw psprecomp::Error("Invalid controller number");return v;};
   auto sequence=parse(a),until=parse(b),buttons=parse(c),x=parse(d),y=parse(e);
   if(sequence>s.sequence){if(buttons>0x3ffff||x>255||y>255||(until&&(until<=frame||until-frame>36000)))throw psprecomp::Error("Controller step outside allowed range");
    s.sequence=sequence;s.until=until;s.buttons=buttons;s.x=x;s.y=y;
    std::ofstream record(s.dir/"commands.log",std::ios::app);record<<s.sequence<<" "<<frame<<" "<<until<<" "<<buttons<<" "<<x<<" "<<y<<"\n";record.close();status(s,frame,filename,false,gpu);
    if(!until)r.stop("Controller diagnostic stop at "+std::to_string(frame));return;
   }
  }}}
  std::this_thread::sleep_for(std::chrono::milliseconds(10));
 }
}
}
