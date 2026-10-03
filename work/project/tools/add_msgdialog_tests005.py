from pathlib import Path
r=Path('/mnt/data/renegade');s=r/'intake/sources/PSPRecomp';host=s/'profiles/renegade/host'
p=host/'psp_services.cpp';t=p.read_text();assert 'run_renegade_message_tests' not in t
code=r'''
// A separate test executable invokes the production utility imports. Inputs
// below are synthetic PSP controller samples, never game memory replacements.
bool run_renegade_message_tests(std::string& error) {
 unsigned checks=0;
 try {
  auto heap=std::make_unique<psprecomp::Runtime>();auto& r=*heap;auto& mem=r.memory();auto& c=r.cpu();
  auto check=[&](bool value,const char* text){++checks;if(!value)throw psprecomp::Error(text);};
  const auto call=[&](std::uint32_t nid,std::uint32_t arg=0){c={};c.pc=0x08801000;c.gpr[31]=0x08801008;c.gpr[4]=arg;r.invoke_import("sceUtility",nid,c);check(!r.stopped(),"message import stopped runtime");return c.gpr[2];};
  constexpr std::uint32_t init=0x2AD8E239,update=0x95FC253B,status=0x9A1C91D7,shutdown=0x67AF3428,abort=0x4928BD96;
  constexpr std::uint32_t p=0x08820000;
  auto prepare=[&](unsigned size=708,unsigned options=0x20,unsigned swap=1,unsigned mode=1){
   for(unsigned i=0;i<1024;++i)mem.store8(p-16+i,0xA5);
   for(unsigned i=0;i<708;++i)mem.store8(p+i,0);
   mem.store32(p,size);mem.store32(p+8,swap);mem.store32(p+0x34,mode);mem.store32(p+0x38,0x80110306);
   if(size>=580)mem.store32(p+0x23c,options);
   std::string text="Synthetic dialog.\nData is not accepted automatically!";
   for(unsigned i=0;i<text.size();++i)mem.store8(p+0x3c+i,text[i]);
   controller_state.buttons=0;
  };
  auto visible=[&]{check(call(status)==1,"init state not exposed");check(call(status)==2,"visible state missing");check(display_window_message_dialog().visible,"host dialog not visible");};
  auto release=[&]{controller_state.buttons=0;check(call(update,1)==0,"release update failed");};
  auto finish=[&](unsigned expected){
   check(call(status)==3,"dialog not awaiting shutdown");check(!display_window_message_dialog().visible,"closed modal still visible");
   check(mem.load32(p+0x1c)==0&&mem.load32(p+0x30)==0,"dialog result fields wrong");
   if(mem.load32(p)>=580)check(mem.load32(p+0x240)==expected,"button result incorrect");
   check(call(update,1)==0x80110001,"update after closure accepted");
   check(call(shutdown)==0,"shutdown rejected");check(call(status)==4,"finished state missing");check(call(status)==0,"finished state not reset");
   for(unsigned i=0;i<16;++i)check(mem.load8(p-16+i)==0xA5&&mem.load8(p+1000+i)==0xA5,"write escaped parameter area");
  };
  for(unsigned lifecycle=0;lifecycle<2;++lifecycle){
   install_profile(r,0x08c40000);check(call(status)==0,"profile did not reset dialog");check(!display_window_message_dialog().visible,"profile leaked host modal");
   for(auto nid:{update,shutdown,abort})check(call(nid)==0x80110001,"inactive utility operation accepted");
   check(call(init,0)==0x80110004,"null argument accepted");check(call(init,0x09fffffe)==0x80110004,"truncated pointer accepted");
   for(unsigned size:{0u,48u,571u,573u,579u,581u,707u,709u,0xffffffffu}){prepare(size);check(call(init,p)==0x80110004,"invalid structure size accepted");check(call(status)==0,"failed init changed state");}
   for(unsigned options:{0x4u,0x30u,0x80000000u}){prepare(708,options);check(call(init,p)==0x80110004,"unknown/conflicting options accepted");}
   prepare(708,0x20,2);check(call(init,p)==0x80110004,"invalid button mapping accepted");
   prepare(708,0x20,1,2);check(call(init,p)==0x80110004,"invalid dialog mode accepted");
   prepare();mem.store8(p+0x3c,0x80);check(call(init,p)==0x80110004,"unsupported text encoding silently accepted");
   prepare();mem.store32(0x09ffff00,708);check(call(init,0x09ffff00)==0x80110004,"parameter crossing RAM boundary accepted");
   // Held confirmation cannot immediately dismiss a newly initialized dialog.
   prepare();controller_state.buttons=0x4000;check(call(init,p)==0,"valid init rejected");check(call(init,p)==0x80110001,"nested dialog accepted");visible();
   check(call(shutdown)==0x80110001,"early shutdown accepted");
   for(unsigned n=0;n<20;++n){check(call(update,1)==0,"visible update error");check(call(status)==2,"held button dismissed modal");}
   release();controller_state.buttons=0x4000;check(call(update,1)==0,"confirm update error");finish(1);
   for(unsigned size:{572u,580u,708u})for(unsigned swap:{0u,1u}){
    prepare(size,0,swap);check(call(init,p)==0,"ABI variant init failed");visible();release();
    controller_state.buttons=swap?0x2000:0x4000;check(call(update,1)==0,"cancel update error");finish(3);
   }
   for(unsigned swap:{0u,1u})for(unsigned selection:{0u,1u,2u}){
    prepare(708,0x110,swap);check(call(init,p)==0,"yes/no init failed");visible();release();
    check(!display_window_message_dialog().selected_yes,"default No not honored");
    if(selection){controller_state.buttons=0x80;call(update,1);release();check(display_window_message_dialog().selected_yes,"Left did not select Yes");}
    if(selection==2){controller_state.buttons=0x20;call(update,1);release();check(!display_window_message_dialog().selected_yes,"Right did not select No");}
    controller_state.buttons=swap?0x4000:0x2000;call(update,1);finish(selection==1?1:2);
   }
   prepare(708,0xA0);check(call(init,p)==0,"no-cancel init failed");visible();release();controller_state.buttons=0x2000;call(update,1);check(call(status)==2,"disabled cancel completed dialog");
   release();controller_state.buttons=0x40;call(update,1);check(display_window_message_dialog().scroll==1,"Down scroll ignored");release();controller_state.buttons=0x10;call(update,1);check(display_window_message_dialog().scroll==0,"Up scroll ignored");
   check(call(abort)==0,"abort failed");finish(0);
   prepare(708,0,1,0);check(call(init,p)==0,"numeric error dialog failed");visible();check(display_window_message_dialog().text.find("80110306")!=std::string::npos,"numeric error code not retained");call(abort);finish(0);
   prepare();check(call(init,p)==0,"second reset init failed");install_profile(r,0x08c40000);check(call(status)==0&&!display_window_message_dialog().visible,"active dialog leaked after profile reset");
  }
  std::cerr<<"PASS "<<checks<<" message-dialog/lifecycle/ABI/input checks\n";error.clear();return true;
 }catch(const std::exception& e){error="after "+std::to_string(checks)+" checks: "+e.what();return false;}
}
'''
t=t[:t.rindex('} // namespace vcs')]+code+t[t.rindex('} // namespace vcs'):];p.write_text(t)
p=host/'display_sdl.cpp';t=p.read_text();needle='   SDL_Event quit{};quit.type=SDL_QUIT;event(quit);';assert t.count(needle)==1
u=r'''   // Actual rendered host-system modal; it is a presentation layer, never a
   // modification of source framebuffer/guest memory. Verify draw and removal.
   auto snapshot=[&]{render(false);int w=0,h=0;SDL_GetRendererOutputSize(renderer,&w,&h);std::vector<unsigned char> out(std::size_t(w)*h*4);checked(SDL_RenderReadPixels(renderer,nullptr,SDL_PIXELFORMAT_RGBA32,out.data(),w*4),"modal readback");return out;};
   const auto before=snapshot();MessageDialogView modal;modal.visible=true;modal.cancel=true;modal.ok=true;modal.text="Data cannot be loaded.\nSystem message requires input.";
   display_window_set_message_dialog(modal);const auto shown=snapshot();std::size_t changes=0;for(std::size_t i=0;i<shown.size();++i)changes+=shown[i]!=before[i];
   check(changes>10000,"system modal did not draw");check(tw==480&&th==272,"modal changed source texture geometry");
   display_window_set_message_dialog({});check(snapshot()==before,"dismissed modal did not restore exact presentation");
   modal.visible=true;modal.text=std::string(512,'\n');modal.scroll=512;display_window_set_message_dialog(modal);render(false);display_window_set_message_dialog({});
   check(wrap_message("abc def ghi",7)==std::vector<std::string>{"ABC DEF"," GHI"},"bounded text wrap changed");
'''
t=t.replace(needle,u+needle);p.write_text(t)
(s/'profiles/renegade/tests/message005.cpp').write_text('#include <iostream>\n#include <string>\nnamespace vcs {bool run_renegade_message_tests(std::string&);}\nint main(){std::string error;if(vcs::run_renegade_message_tests(error))return 0;std::cerr<<error<<"\\n";return 1;}\n')
p=s/'profiles/renegade/CMakeLists.txt';p.write_text(p.read_text()+'''\nadd_executable(renegade_message_tests tests/message005.cpp)
target_link_libraries(renegade_message_tests PRIVATE renegade_services)
add_test(NAME renegade_message_tests COMMAND renegade_message_tests)
set_tests_properties(renegade_message_tests PROPERTIES ENVIRONMENT "PSPRECOMP_WINDOW=0;PSPRECOMP_AUDIO=0;PSPRECOMP_FRAME_LIMIT=0")
''')
p=r/'tools/package005.py';p.write_text(p.read_text().replace("'profiles/renegade/tests/clock004.cpp']","'profiles/renegade/tests/clock004.cpp','profiles/renegade/host/message_dialog.hpp','profiles/renegade/tests/message005.cpp']"))
print('Registered HLE and presentation regressions added')
