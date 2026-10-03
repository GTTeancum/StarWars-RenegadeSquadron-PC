#include "modern_input008.hpp"
#include "psprecomp/common.hpp"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <string>
namespace renegade::input008 { namespace {
Config cfg;
Frame now;
Frame unfiltered009;
bool initialized=false;
std::uint64_t frame=0,last_polled=~std::uint64_t(0),diagnostic_sequence=0;
std::array<bool,28> previous{},pending{};
std::array<bool,28> delivered_interaction{};
std::uint64_t delivered_frame=0;
std::array<std::uint64_t,28> expires{};
bool was_enabled=false,have_sample=false;
std::uint32_t blocked_buttons=0;
bool blocked_lt=false,blocked_rt=false;
float env_float(const char* name,float value,float minimum,float maximum) {
 const char* p=std::getenv(name);if(!p)return value;
 std::size_t used=0;const std::string text(p);float v;
 try{v=std::stof(text,&used);}catch(...){throw psprecomp::Error(std::string("Invalid ")+name);}
 if(used!=text.size()||!std::isfinite(v)||v<minimum||v>maximum)
  throw psprecomp::Error(std::string("Out-of-range ")+name);
 return v;
}
std::array<float,2> stick(std::int16_t ix,std::int16_t iy,float deadzone,float curve) {
 const float x=ix<0?float(ix)/32768.f:float(ix)/32767.f;
 const float y=iy<0?float(iy)/32768.f:float(iy)/32767.f;
 const float magnitude=std::hypot(x,y);
 if(magnitude<=deadzone)return {0,0};
 const float t=std::pow((std::min(magnitude,1.f)-deadzone)/(1.f-deadzone),curve);
 return {x/magnitude*t,y/magnitude*t};
}
void validate(const Config& c) {
 if(!std::isfinite(c.left_deadzone)||!std::isfinite(c.right_deadzone)||
    c.left_deadzone<0||c.left_deadzone>=1||c.right_deadzone<0||c.right_deadzone>=1||
    !std::isfinite(c.look_x)||!std::isfinite(c.look_y)||c.look_x<0||c.look_x>4||c.look_y<0||c.look_y>4||
    !std::isfinite(c.curve)||c.curve<1||c.curve>3||
    !std::isfinite(c.trigger_threshold)||c.trigger_threshold<0||c.trigger_threshold>=1)
  throw psprecomp::Error("Invalid modern control configuration");
}
std::array<bool,28> action_buttons(const Frame& f) {
 std::array<bool,28> a{};
 if(!f.active||!f.enabled)return a;
 const auto held=[&](Button b){return (f.buttons&bit(b))!=0;};
 a[11]=held(A);a[17]=f.left_trigger>cfg.trigger_threshold;
 a[18]=held(RightStick);a[20]=held(LeftShoulder);
 a[22]=held(Y)||held(Left);a[23]=held(Right);
 a[24]=a[25]=held(X);
 return a;
}
RawPad diagnostic_sample(const char* file) {
 static RawPad held;
 std::ifstream in(file);
 if(!in)return {}; // absent file means no diagnostic controller, not a held old one
 std::string text;std::getline(in,text);std::istringstream row(text);
 unsigned long long seq;int connected,lx,ly,rx,ry,lt,rt;unsigned buttons;std::string extra;
 if(!(row>>seq>>connected>>lx>>ly>>rx>>ry>>lt>>rt>>buttons)||(row>>extra)||
    (connected!=0&&connected!=1)||lx<-32768||lx>32767||ly<-32768||ly>32767||
    rx<-32768||rx>32767||ry<-32768||ry>32767||lt<0||lt>32767||rt<0||rt>32767||
    buttons>0x7fffu)throw psprecomp::Error("Invalid RENEGADE_GAMEPAD_DIAGNOSTIC sample");
 if(seq<diagnostic_sequence)throw psprecomp::Error("Gamepad diagnostic sequence moved backwards");
 if(seq>diagnostic_sequence) {
  diagnostic_sequence=seq;held={connected!=0,connected!=0,
   std::int16_t(lx),std::int16_t(ly),std::int16_t(rx),std::int16_t(ry),
   std::int16_t(lt),std::int16_t(rt),buttons};
  std::cerr<<"[gamepad008] frame="<<frame<<" sequence="<<seq<<" connected="<<connected
   <<" sticks="<<lx<<","<<ly<<","<<rx<<","<<ry<<" triggers="<<lt<<","<<rt
   <<" buttons="<<buttons<<" (controller input only)\n";
 }
 return held;
}
}
bool modern_enabled() {
 const char* v=std::getenv("RENEGADE_CONTROLS");
 if(!v||std::string(v)=="legacy")return false;
 if(std::string(v)!="modern")throw psprecomp::Error("RENEGADE_CONTROLS must be legacy or modern");
 return true;
}
Config config_from_environment() {
 Config c;
 c.left_deadzone=env_float("RENEGADE_LEFT_DEADZONE",c.left_deadzone,0,.9f);
 c.right_deadzone=env_float("RENEGADE_RIGHT_DEADZONE",c.right_deadzone,0,.9f);
 c.look_x=env_float("RENEGADE_LOOK_X",1,.05f,4);
 c.look_y=env_float("RENEGADE_LOOK_Y",1,.05f,4);
 c.curve=env_float("RENEGADE_LOOK_CURVE",1,1,3);
 c.trigger_threshold=env_float("RENEGADE_TRIGGER_THRESHOLD",c.trigger_threshold,0,.95f);
 const char* invert=std::getenv("RENEGADE_INVERT_Y");
 if(invert&&std::string(invert)!="0"&&std::string(invert)!="1")
  throw psprecomp::Error("RENEGADE_INVERT_Y must be 0 or 1");
 c.invert_y=invert&&*invert=='1';return c;
}
Frame normalize(const RawPad& r,const Config& c) {
 validate(c);Frame f;f.active=r.connected;f.enabled=r.enabled&&r.connected;
 if(!f.enabled)return f;
 auto l=stick(r.lx,r.ly,c.left_deadzone,1);
 auto right=stick(r.rx,r.ry,c.right_deadzone,c.curve);
 f.move_x=l[0];f.move_y=-l[1];
 f.look_x=right[0]*c.look_x;f.look_y=-right[1]*c.look_y*(c.invert_y?-1.f:1.f);
 f.left_trigger=std::clamp(float(r.lt)/32767.f,0.f,1.f);
 f.right_trigger=std::clamp(float(r.rt)/32767.f,0.f,1.f);
 f.buttons=r.buttons&0x7fff;return f;
}
void reset(const Config& c) {
 validate(c);cfg=c;now={};unfiltered009={};frame=0;last_polled=~std::uint64_t(0);
 diagnostic_sequence=0;previous.fill(false);pending.fill(false);expires.fill(0);
 delivered_interaction.fill(false);delivered_frame=0;
 was_enabled=false;have_sample=false;blocked_buttons=0;blocked_lt=blocked_rt=false;initialized=true;
}
void reset(){reset(config_from_environment());}
void accept_sample(std::uint64_t n,const RawPad& raw) {
 if(!initialized)reset();
 frame=n;now=normalize(raw,cfg);unfiltered009=now;
 if(n!=delivered_frame){delivered_interaction.fill(false);delivered_frame=n;}
 if(!now.enabled){
  previous.fill(false);pending.fill(false);expires.fill(0);
  delivered_interaction.fill(false);
  was_enabled=false;have_sample=true;return;
 }
 if(have_sample&&!was_enabled) {
  blocked_buttons=now.buttons;
  blocked_lt=now.left_trigger>cfg.trigger_threshold;
  blocked_rt=now.right_trigger>cfg.trigger_threshold;
 }
 blocked_buttons&=now.buttons;
 now.buttons&=~blocked_buttons;
 if(now.left_trigger<=cfg.trigger_threshold)blocked_lt=false;
 if(now.right_trigger<=cfg.trigger_threshold)blocked_rt=false;
 if(blocked_lt)now.left_trigger=0;
 if(blocked_rt)now.right_trigger=0;
 const auto next=action_buttons(now);
 for(unsigned i=0;i<28;++i){
  if(n>expires[i])pending[i]=false;
  if(!previous[i]&&next[i]){pending[i]=true;expires[i]=n+4;}
  previous[i]=next[i];
 }
 was_enabled=true;have_sample=true;
}
void frame_tick(std::uint64_t n) {
 if(!initialized)reset();
 if(n==last_polled)return;
 last_polled=n;frame=n;
 if(!modern_enabled()){accept_sample(n,{});return;}
 const char* file=std::getenv("RENEGADE_GAMEPAD_DIAGNOSTIC");
 accept_sample(n,file?diagnostic_sample(file):live_gamepad());
}
void quarantine_held_actions009() {
 // Observe only the most recent physical/diagnostic sample. Never alter PSP memory.
 // A button used by a menu must be released before it becomes a gameplay action.
 pending.fill(false);expires.fill(0);previous.fill(false);
 delivered_interaction.fill(false);
 blocked_buttons|=unfiltered009.buttons;
 blocked_lt=blocked_lt||unfiltered009.left_trigger>cfg.trigger_threshold;
 blocked_rt=blocked_rt||unfiltered009.right_trigger>cfg.trigger_threshold;
 now.buttons&=~blocked_buttons;
 if(blocked_lt)now.left_trigger=0;
 if(blocked_rt)now.right_trigger=0;
}
Frame current(){return now;}
float trigger_threshold(){return cfg.trigger_threshold;}
std::uint64_t frame_number(){return frame;}
bool pending_action(unsigned i) {
 if(i>=pending.size())return false;
 // The original interaction values remain readable by multiple consumers in
 // one simulation frame. Clearing on the first getter hid the equipment-menu
 // request from its later consumer (observed in the native command-post run).
 const bool interaction=i==24||i==25;
 if(interaction&&delivered_interaction[i]&&delivered_frame==frame)return true;
 const bool v=pending[i]&&frame<=expires[i];pending[i]=false;
 if(interaction&&v){delivered_interaction[i]=true;delivered_frame=frame;}
 return v;
}
}
