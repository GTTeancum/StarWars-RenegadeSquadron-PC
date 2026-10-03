from pathlib import Path
S=Path('/mnt/data/renegade/intake/sources/PSPRecomp');H=S/'profiles/renegade/host'
(H/'diagnostic_control.hpp').write_text('''#pragma once
#include "psprecomp/runtime.hpp"
#include "framebuffer_capture.hpp"
#include <utility>
namespace renegade {
void control_vblank(psprecomp::Runtime&,const vcs::FramebufferDescription&,std::uint64_t);
std::uint32_t control_buttons(std::uint64_t);
bool control_analog(std::uint64_t,std::uint8_t&,std::uint8_t&);
}
''')
(H/'diagnostic_control.cpp').write_text(r'''// Optional controller-only bounded stepping. No guest-state mutation or save-state injection.
#include "diagnostic_control.hpp"
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <thread>
#include <chrono>
#include <iostream>
namespace renegade { namespace {
struct State {std::filesystem::path dir;std::uint64_t sequence{},until{};std::uint32_t buttons{};std::uint8_t x{128},y{128};bool enabled{};};
State& state(){static State s=[] {State a;const char* d=std::getenv("RENEGADE_CONTROL_DIRECTORY");if(!d||!*d)return a;a.dir=d;std::filesystem::create_directories(a.dir);a.enabled=true;if(const char* n=std::getenv("RENEGADE_CONTROL_START")){std::size_t used;std::string t=n;a.until=std::stoull(t,&used,0);if(used!=t.size())throw psprecomp::Error("Bad control-start value");}return a;}();return s;}
void status(State& s,std::uint64_t frame,const std::string& image,bool paused){auto p=s.dir/"status.json";auto temp=p;temp+=".tmp";{std::ofstream f(temp);f<<"{\"sequence\":"<<s.sequence<<",\"vblank\":"<<frame<<",\"until\":"<<s.until<<",\"paused\":"<<(paused?"true":"false")<<",\"frame\":\""<<image<<"\"}\n";if(!f)throw psprecomp::Error("Cannot save controller-step status");}std::filesystem::rename(temp,p);}
}
std::uint32_t control_buttons(std::uint64_t frame){auto& s=state();return s.enabled && frame<s.until?s.buttons:0;}
bool control_analog(std::uint64_t frame,std::uint8_t& x,std::uint8_t& y){auto& s=state();if(!s.enabled || !s.sequence || frame>=s.until)return false;x=s.x;y=s.y;return true;}
void control_vblank(psprecomp::Runtime& r,const vcs::FramebufferDescription& desc,std::uint64_t frame){auto& s=state();if(!s.enabled || frame<s.until)return;
 auto filename="pause_"+std::to_string(s.sequence)+"_vblank_"+std::to_string(frame)+".ppm";
 vcs::write_framebuffer_ppm(s.dir/filename,desc,vcs::decode_framebuffer_rgb(r.memory(),desc));status(s,frame,filename,true);
 std::cerr<<"[controller-step] paused vblank="<<frame<<" sequence="<<s.sequence<<"\n";
 for(;;){
  std::ifstream in(s.dir/"command.txt");if(in){std::string a,b,c,d,e,junk;if((in>>a>>b>>c>>d>>e)&&!(in>>junk)){
   auto parse=[](const std::string& text){if(text.empty()||text[0]=='-')throw psprecomp::Error("Negative controller command");std::size_t n;auto v=std::stoull(text,&n,0);if(n!=text.size())throw psprecomp::Error("Invalid controller number");return v;};
   auto sequence=parse(a),until=parse(b),buttons=parse(c),x=parse(d),y=parse(e);
   if(sequence>s.sequence){if(buttons>0x3ffff||x>255||y>255||(until&&(until<=frame||until-frame>36000)))throw psprecomp::Error("Controller step outside allowed range");
    s.sequence=sequence;s.until=until;s.buttons=buttons;s.x=x;s.y=y;
    std::ofstream record(s.dir/"commands.log",std::ios::app);record<<s.sequence<<" "<<frame<<" "<<until<<" "<<buttons<<" "<<x<<" "<<y<<"\n";record.close();status(s,frame,filename,false);
    if(!until)r.stop("Controller diagnostic stop at "+std::to_string(frame));return;
   }
  }}
  std::this_thread::sleep_for(std::chrono::milliseconds(10));
 }
}
}
''')
p=H/'psp_services.cpp';t=p.read_text();t='#include "diagnostic_control.hpp"\n'+t
t=t.replace('std::uint32_t buttons = controller_state.buttons | display_window_buttons();','std::uint32_t buttons = controller_state.buttons | display_window_buttons() | renegade::control_buttons(display_vblank_index);')
t=t.replace('    return {analog_x, analog_y};','    (void)renegade::control_analog(display_vblank_index, analog_x, analog_y);\n    return {analog_x, analog_y};',1)
t=t.replace('        capture_frame_if_requested(rt.memory(), displayed);','        capture_frame_if_requested(rt.memory(), displayed);\n        renegade::control_vblank(rt, displayed, display_vblank_index);\n        if (rt.stopped()) return;',1);p.write_text(t)
p=S/'profiles/renegade/CMakeLists.txt';t=p.read_text().replace('host/audio_sdl.cpp)','host/audio_sdl.cpp host/diagnostic_control.cpp)');p.write_text(t)
p=H/'main.cpp';t=p.read_text().replace('reason.find("VBlank diagnostic stop")==0','reason.find("VBlank diagnostic stop")==0 || reason.find("Controller diagnostic stop")==0');p.write_text(t)
