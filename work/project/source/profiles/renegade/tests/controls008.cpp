#include "../host/modern_input008.hpp"
#include "psprecomp/runtime.hpp"
#include "display_window.hpp"
#include <SDL2/SDL.h>
#include "../host/test_environment010.hpp"
#include <array>
#include <bit>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <string>
using namespace renegade::input008;
int main(){
 unsigned checks=0,fail=0;
 auto check=[&](bool ok,const char* why){++checks;if(!ok){++fail;std::cerr<<"FAIL "<<why<<"\n";}};
 Config c;RawPad r{true,true};reset(c);
 for(int x=-32768;x<=32767;x+=257)for(int y=-32768;y<=32767;y+=257) {
  r.lx=x;r.ly=y;r.rx=x;r.ry=y;auto f=normalize(r,c);
  check(std::hypot(f.move_x,f.move_y)<=1.000001f,"move radial clamp");
  check(std::hypot(f.look_x,f.look_y)<=1.000001f,"look radial clamp");
  if(std::hypot(float(x),float(y))<7800)check(f.move_x==0&&f.move_y==0,"left drift");
  if(std::hypot(float(x),float(y))<8600)check(f.look_x==0&&f.look_y==0,"right drift");
  check(std::isfinite(f.move_x)&&std::isfinite(f.look_y),"finite axes");
 }
 r={true,true};r.rx=32767;r.ly=-32768;auto n=normalize(r,c);
 check(n.move_y==1&&n.move_x==0&&n.look_x==1&&n.look_y==0,"independent full axes");
 r={true,true};r.ry=-32768;check(normalize(r,c).look_y==1,"normal up");
 c.invert_y=true;check(normalize(r,c).look_y==-1,"invert only Y");c.invert_y=false;
 r.rt=-32768;r.lt=32767;n=normalize(r,c);check(n.right_trigger==0&&n.left_trigger==1,"trigger domains");
 r.connected=false;n=normalize(r,c);check(!n.active&&n.look_y==0&&n.left_trigger==0,"disconnect neutral");
 r.connected=true;r.enabled=false;n=normalize(r,c);check(n.active&&!n.enabled&&n.look_y==0,"focus neutral without legacy fallback");
 r={true,true};r.buttons=bit(A)|bit(X);accept_sample(1,r);
 check(pending_action(11)&&!pending_action(11),"jump one-shot");
 check(pending_action(24)&&pending_action(25),"independent interact consumers");
 accept_sample(2,r);check(!pending_action(11),"held jump not repeated");
 r.buttons=0;accept_sample(3,r);r.buttons=bit(A);accept_sample(4,r);check(pending_action(11),"second press rearmed");
 accept_sample(5,r);r.enabled=false;accept_sample(6,r);check(!pending_action(11),"focus flushes events");
 r.enabled=true;accept_sample(7,r);r.connected=false;accept_sample(8,r);check(!pending_action(11),"disconnect flushes events");
 
 reset(c);r={true,true};r.buttons=bit(A);accept_sample(20,r);
 accept_sample(26,r);check(!pending_action(11),"menu-confirm edge expires before future gameplay");
 r.enabled=false;accept_sample(27,r);r.enabled=true;accept_sample(28,r);
 check(!pending_action(11)&&(current().buttons&bit(A))==0,"held confirm after focus return blocked");
 r.buttons=0;accept_sample(29,r);r.buttons=bit(A);accept_sample(30,r);
 check(pending_action(11),"release and repress after focus works");
 // Invoke the exact production leaf: other callers and out-of-range actions must
 // retain every original temporary register and f0. Inputs remain read-only.
 auto rt=std::make_unique<psprecomp::Runtime>();auto& m=rt->memory();
 constexpr unsigned map=0x08810000,values=0x08811000;
 m.store32(map,28);m.store32(map+12,values);
 for(unsigned i=0;i<28;++i)m.store32(values+4*i,std::bit_cast<unsigned>(float(i)+.125f));
 for(unsigned caller:{0x08812340u,0x08A5F164u})for(unsigned i=0;i<31;++i) {
  reset(c);psprecomp::AllegrexContext ctx{};ctx.gpr[4]=map;ctx.gpr[5]=i;ctx.gpr[31]=caller;
  action_getter(*rt,ctx);
  check(ctx.pc==caller&&ctx.gpr[3]==i*4&&ctx.gpr[5]==unsigned(i<28),"leaf original regs");
  check(ctx.gpr[2]==(i<28?values+4*i:28),"leaf original v0");
  check(ctx.fpr[0]==(i<28?float(i)+.125f:0.f),"inactive pad original return");
 }
 renegade::test010::set_environment("RENEGADE_CONTROLS","modern");
 r={true,true};r.lx=32767;r.ry=-32768;r.rt=32767;r.buttons=bit(A)|bit(X)|bit(LeftStick);
 reset(c);accept_sample(10,r);
 auto get=[&](unsigned i,unsigned caller=0x08A5F164u){
  psprecomp::AllegrexContext ctx{};ctx.gpr[4]=map;ctx.gpr[5]=i;ctx.gpr[31]=caller;
  action_getter(*rt,ctx);return ctx.fpr[0];};
 check(get(0)==0&&get(2)==0&&get(1)==1&&get(3)==1,"RS only look");
 check(get(4)==0&&get(5)==1,"LS strafe without lock");
 check(get(8)==1&&get(16)==0,"independent fire without aim");
 check(get(11)==1&&get(11)==0,"A jump not fire");
 check(get(21)==1,"L3 sprint");
 check(get(10)==1&&get(24)==1&&get(25)==1,"X interact hold and edges");
 check(get(25)==1&&get(24)==1,"interaction pulse survives multiple consumers in one frame");
 accept_sample(11,r);
 check(get(24)==0&&get(25)==0,"consumed interaction pulse does not repeat next frame");
 check(get(0,0x08812340)==.125f,"foreign caller untouched");
 check(m.load32(values+8)==std::bit_cast<unsigned>(2.125f),"input table never modified");
 r={true,true};r.buttons=bit(Up);reset(c);accept_sample(40,r);
 check(get(26)==1&&get(27)==0,"D-pad Up supplies jetpack rise only");
 check(get(10)==0&&get(24)==0&&get(25)==0&&get(11)==0,"rise does not interact or toggle jetpack");
 r.buttons=bit(Down);accept_sample(41,r);
 check(get(26)==0&&get(27)==1&&get(20)==0,"D-pad Down descends without secondary selection");
 r.buttons=bit(Up)|bit(Down);accept_sample(42,r);
 check(get(26)==1&&get(27)==1,"both height inputs preserve original opposing-action cancellation");
 check(get(26,0x08812340)==26.125f&&get(27,0x08812340)==27.125f,"foreign height callers unchanged");
 r.enabled=false;accept_sample(43,r);
 for(unsigned i:{0u,1u,2u,3u,4u,5u,8u,9u,10u,11u,16u,17u,18u,20u,21u,22u,23u,24u,25u,26u,27u})
  check(get(i)==0,"suppressed input neutral");
 // Real SDL virtual gamepad uses the same production sampler as physical pads.
 SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");
 vcs::display_window_start();
 int device=SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,6,15,0);
 check(device>=0,"SDL virtual controller attach");
 SDL_Joystick* joy=SDL_JoystickOpen(device);
 check(joy!=nullptr,"SDL virtual joystick handle");
 char guid[64]{};SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(device),guid,sizeof(guid));
 char* mapped=SDL_GameControllerMappingForGUID(SDL_JoystickGetDeviceGUID(device));
 std::cerr<<"[virtual-map] "<<(mapped?mapped:"<none>")<<"\n";SDL_free(mapped);
 SDL_Window* test_window=SDL_GetWindowFromID(1);check(test_window!=nullptr,"fixture window lookup");
 const unsigned wid=test_window?SDL_GetWindowID(test_window):0;
 SDL_Event event{};event.type=SDL_WINDOWEVENT;event.window.windowID=wid;event.window.event=SDL_WINDOWEVENT_FOCUS_GAINED;SDL_PushEvent(&event);
 // Open through the production add-device event at released-trigger state
 // before changing axes, as a real hotplug/open lifecycle does.
 SDL_JoystickSetVirtualAxis(joy,SDL_CONTROLLER_AXIS_TRIGGERLEFT,-32768);
 SDL_JoystickSetVirtualAxis(joy,SDL_CONTROLLER_AXIS_TRIGGERRIGHT,-32768);
 SDL_JoystickUpdate();(void)live_gamepad();
 SDL_JoystickSetVirtualAxis(joy,SDL_CONTROLLER_AXIS_LEFTX,16384);
 SDL_JoystickSetVirtualAxis(joy,SDL_CONTROLLER_AXIS_RIGHTX,-32768);
 SDL_JoystickSetVirtualAxis(joy,SDL_CONTROLLER_AXIS_RIGHTY,32767);
 SDL_JoystickSetVirtualAxis(joy,SDL_CONTROLLER_AXIS_TRIGGERLEFT,-32768);
 SDL_JoystickSetVirtualAxis(joy,SDL_CONTROLLER_AXIS_TRIGGERRIGHT,32767);
 SDL_JoystickSetVirtualButton(joy,SDL_CONTROLLER_BUTTON_A,1);
 SDL_JoystickUpdate();auto live=live_gamepad();
 check(live.connected&&live.enabled,"production SDL discovers virtual controller");
 check(live.lx==16384&&live.rx==-32768&&live.ry==32767,"production SDL reads independent axes");
 std::cerr<<"[virtual-state] lt="<<live.lt<<" rt="<<live.rt<<" focus="<<live.enabled<<"\n";
 check(live.lt==0&&live.rt==32767,"SDL trigger mapping distinct");
 check((live.buttons&bit(A))!=0,"SDL semantic A mapping");
 event.window.event=SDL_WINDOWEVENT_FOCUS_LOST;SDL_PushEvent(&event);live=live_gamepad();
 check(live.connected&&!live.enabled&&live.rx==0&&live.buttons==0,"SDL focus-loss clears look and buttons");
 event.window.event=SDL_WINDOWEVENT_FOCUS_GAINED;SDL_PushEvent(&event);live=live_gamepad();
 check(live.enabled,"SDL focus regain");
 SDL_Event key{};key.type=SDL_KEYDOWN;key.key.windowID=wid;key.key.keysym.scancode=SDL_SCANCODE_R;key.key.keysym.mod=KMOD_ALT;SDL_PushEvent(&key);
 live=live_gamepad();check(live.connected&&!live.enabled&&live.rx==0,"resolution dropdown isolates both sticks");
 SDL_JoystickClose(joy);SDL_JoystickDetachVirtual(device);live=live_gamepad();
 check(!live.connected&&live.rx==0,"SDL unplug flushes input");
 vcs::display_window_shutdown();
 std::cout<<"controls008_checks="<<checks<<" failures="<<fail<<"\n";return fail?1:0;
}
