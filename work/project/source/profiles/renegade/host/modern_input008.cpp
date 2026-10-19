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
bool kbm_active=false; // which device spoke last: the keyboard/mouse or the pad
// Mouse look filter state (Asura_ControlMapping_Axis::m_fValueToReport per axis).
float mouse_look_x=0.f,mouse_look_y=0.f;
// Sprint toggle state: latched on a press, cleared by a second press or by the
// player standing still for a short while (as PC shooters with toggle sprint do).
bool sprint_on=false,sprint_was_held=false,sprint_moved=false; int sprint_still_frames=0;
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
 c.invert_y=invert&&*invert=='1';
 c.mouse_sensitivity=env_float("RENEGADE_MOUSE_SENSITIVITY",1,.05f,10);
 const char* minvert=std::getenv("RENEGADE_MOUSE_INVERT_Y");
 c.mouse_invert_y=minvert&&*minvert=='1';
 c.mouse_smoothing=env_float("RENEGADE_MOUSE_SMOOTHING",c.mouse_smoothing,0,.25f);
 const char* sprint=std::getenv("RENEGADE_SPRINT_TOGGLE");
 c.sprint_toggle=!(sprint&&*sprint=='0');
 const char* centering=std::getenv("RENEGADE_VIEW_CENTERING");
 c.view_centering=centering&&*centering=='1';return c;
}
Frame normalize(const RawPad& r,const Config& c) {
 validate(c);Frame f;f.active=r.connected;f.enabled=r.enabled&&r.connected;
 if(!f.enabled)return f;
 auto l=stick(r.lx,r.ly,c.left_deadzone,1);
 auto right=stick(r.rx,r.ry,c.right_deadzone,c.curve);
 f.move_x=l[0];f.move_y=-l[1];
 f.look_x=right[0]*c.look_x;f.look_y=-right[1]*c.look_y*(c.invert_y?-1.f:1.f);
 if(r.mouse_look) {
  // Asura PC turns the mouse motion of a frame into a velocity
  // (Asura_Mouse::OncePerFrameUpdate: delta * frame rate) and feeds it to the
  // look axis through Asura_ControlMapping_Axis, whose response time eases the
  // reported value toward the input (value += (input - value) * min(dt/time, 1)),
  // with the decay using the same time. Samples arrive once per vblank (60 Hz)
  // while the game reads the look axes on its own frames, so the filter also
  // carries motion from vblanks the game did not read instead of dropping it.
  // Calibration: 480 px/s is a full turn stick at sensitivity 1; the game's
  // own turn rate caps faster motion.
  constexpr float vblank_seconds=1.f/60.f,pixels_per_second_for_full=480.f;
  const float vx=r.mouse_dx/vblank_seconds,vy=-r.mouse_dy/vblank_seconds;
  const float scale=c.mouse_smoothing>0.f?std::min(vblank_seconds/c.mouse_smoothing,1.f):1.f;
  mouse_look_x+=(vx-mouse_look_x)*scale;
  mouse_look_y+=(vy-mouse_look_y)*scale;
  if(std::abs(mouse_look_x)<1.f)mouse_look_x=0.f; // settle exactly at rest (below 1 px/s)
  if(std::abs(mouse_look_y)<1.f)mouse_look_y=0.f;
  f.look_x=std::clamp(mouse_look_x*c.mouse_sensitivity/pixels_per_second_for_full,-1.f,1.f);
  f.look_y=std::clamp(mouse_look_y*c.mouse_sensitivity/pixels_per_second_for_full,-1.f,1.f)*(c.mouse_invert_y?-1.f:1.f);
  static const bool diagnostics=std::getenv("RENEGADE_MOUSE_LOOK_DIAG")!=nullptr;
  if(diagnostics&&(r.mouse_dx!=0.f||f.look_x!=0.f))std::cerr<<"[mouse-look] frame="<<frame<<" dx="<<r.mouse_dx<<" look_x="<<f.look_x<<"\n";
 } else {
  mouse_look_x=mouse_look_y=0.f; // the pad owns the frame; the mouse starts fresh next time
 }
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
 {
  const bool held=now.enabled&&(now.buttons&bit(LeftStick));
  if(held&&!sprint_was_held){sprint_on=!sprint_on;sprint_moved=false;sprint_still_frames=0;}
  sprint_was_held=held;
  const bool moving=std::hypot(now.move_x,now.move_y)>0.2f;
  if(moving&&sprint_on)sprint_moved=true;
  sprint_still_frames=moving?0:sprint_still_frames+1;
  // Stopping ends a sprint; a tap before moving stays armed for a moment.
  if((sprint_moved&&sprint_still_frames>20)||sprint_still_frames>90||!now.enabled)sprint_on=false;
 }
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
 if(file){accept_sample(n,diagnostic_sample(file));return;}
 // Whichever device the player touched last owns the frame; a connected pad
 // keeps the sample "connected" so a quiet keyboard still counts as a pad.
 const RawPad pad=live_gamepad(),kbm=live_keyboard_mouse();
 const bool pad_activity=pad.connected&&pad.enabled&&(pad.buttons||std::abs(int(pad.lx))>12000||std::abs(int(pad.ly))>12000||std::abs(int(pad.rx))>12000||std::abs(int(pad.ry))>12000||pad.lt>8000||pad.rt>8000);
 if(kbm.activity)kbm_active=true; else if(pad_activity)kbm_active=false;
 if(kbm_active&&kbm.enabled)accept_sample(n,kbm); else accept_sample(n,pad.connected?pad:kbm);
}
bool keyboard_mouse_active(){return kbm_active;}
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
bool sprint_active(){
 if(!now.enabled)return false;
 return cfg.sprint_toggle?sprint_on:(now.buttons&bit(LeftStick))!=0;
}
Config config(){if(!initialized)reset();return cfg;}
void set_config(const Config& c){validate(c);if(!initialized)reset();cfg=c;}
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
