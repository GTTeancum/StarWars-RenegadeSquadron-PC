#!/usr/bin/env python3
"""Original implementation of bounded PSP utility message dialogs.
ABI field/NID facts: bundled PSPSDK src/utility headers and import stubs.
Extended size/flag facts checked against the PPSSPP reference interface;
no PPSSPP implementation, rendering, fonts or licensed game code is copied.
"""
from pathlib import Path
r=Path('/mnt/data/renegade');s=r/'intake/sources/PSPRecomp';host=s/'profiles/renegade/host'
header='''#pragma once
#include <cstdint>
#include <string>
namespace vcs {
// Host presentation of a PSP system message. This is not a guest-state override.
struct MessageDialogView {
    bool visible{}, yes_no{}, ok{}, cancel{}, accept_cross{true}, selected_yes{true};
    unsigned scroll{};
    std::string text;
};
void display_window_set_message_dialog(const MessageDialogView& view);
MessageDialogView display_window_message_dialog();
}
'''
(host/'message_dialog.hpp').write_text(header)
p=host/'display_sdl.cpp';t=p.read_text();assert 'message_dialog.hpp' not in t
t=t.replace('#include "display_ui.hpp"','#include "display_ui.hpp"\n#include "message_dialog.hpp"\n#include <cctype>')
t=t.replace('std::string capture_request;','std::string capture_request;\nMessageDialogView message_view;')
t=t.replace(" case '-':return", " case '?':return {14,17,1,2,4,0,4}; case '!':return {4,4,4,4,4,0,4};\n case ',':return {0,0,0,0,6,4,8}; case '\\'':return {4,4,8,0,0,0,0};\n case '=':return {0,31,0,31,0,0,0};\n case '-':return")
start=t.index('void render(bool present=true)')
ui='''// Original host modal; source framebuffer pixels and game state are unchanged.
std::vector<std::string> wrap_message(const std::string& input, unsigned columns) {
 std::vector<std::string> result; std::string line;
 for(unsigned char byte:input) {
  if(byte=='\\r')continue;
  if(byte=='\\n'){result.push_back(line);line.clear();continue;}
  const char c=byte=='\\t'?' ':char(std::toupper(byte));
  line.push_back(c);
  if(line.size()>=columns) {
   const auto space=line.find_last_of(' ');
   if(space!=std::string::npos&&space>columns/2){result.push_back(line.substr(0,space));line.erase(0,space+1);}
   else {result.push_back(line);line.clear();}
  }
 }
 if(!line.empty()||result.empty())result.push_back(line);
 return result;
}
void draw_message_dialog(int ww,int wh) {
 if(!message_view.visible||ww<80||wh<100)return;
 const int scale=ww>=800?2:1;
 const int margin=12*scale,panel_width=std::min(ww-24,900),line_height=10*scale;
 const unsigned columns=unsigned(std::max(1,(panel_width-2*margin)/(6*scale)));
 const auto lines=wrap_message(message_view.text,columns);
 const int maximum_height=wh-ui::toolbar_height-16;
 const unsigned capacity=unsigned(std::max(1,(maximum_height-64*scale)/line_height));
 const unsigned shown=std::min(capacity,unsigned(lines.size()));
 const unsigned offset=std::min(message_view.scroll,unsigned(lines.size())-shown);
 const int height=int(shown)*line_height+64*scale;
 const int x=(ww-panel_width)/2,y=ui::toolbar_height+std::max(8,(wh-ui::toolbar_height-height)/2);
 fill({x,y,panel_width,height},{24,31,43,255});
 fill({x,y,panel_width,2},{99,179,225,255});
 text(x+margin,y+10*scale,"PSP SYSTEM MESSAGE",{162,213,245,255},scale);
 SDL_Rect clip{x+margin,y+25*scale,panel_width-2*margin,int(shown)*line_height};
 checked(SDL_RenderSetClipRect(renderer,&clip),"message text clip");
 for(unsigned i=0;i<shown;++i)text(x+margin,y+25*scale+int(i)*line_height,lines[offset+i],{238,243,250,255},scale);
 checked(SDL_RenderSetClipRect(renderer,nullptr),"message clip reset");
 int by=y+25*scale+int(shown)*line_height;
 if(lines.size()>shown)text(x+margin,by,"UP/DOWN TO SCROLL",{162,181,206,255},scale);
 by+=12*scale;
 if(message_view.yes_no) {
  text(x+margin,by,message_view.selected_yes?"(YES)    NO":" YES    (NO)",{133,215,247,255},scale);
  by+=11*scale;
 }
 std::string hint;
 if(message_view.yes_no||message_view.ok)hint=message_view.accept_cross?"CROSS: CONFIRM":"CIRCLE: CONFIRM";
 if(message_view.cancel){if(!hint.empty())hint+="  ";hint+=message_view.accept_cross?"CIRCLE: BACK":"CROSS: BACK";}
 if(hint.empty())hint="WAITING FOR APPLICATION";
 text(x+margin,by,hint,{194,212,233,255},scale);
}
'''
t=t[:start]+ui+t[start:]
t=t.replace(' if(menu_open) {\n  fill(', ' draw_message_dialog(ww,wh);\n if(menu_open) {\n  fill(',1)
# Exported view state is separately owned from input; opening a dialog cannot
# synthesize a confirmation button. Both utility lifecycle and tests own reset.
idx=t.index('void display_window_start(')
t=t[:idx]+'''void display_window_set_message_dialog(const MessageDialogView& view) {
 message_view=view; if(message_view.text.size()>512)message_view.text.resize(512); render();
}
MessageDialogView display_window_message_dialog() { return message_view; }
'''+t[idx:]
p.write_text(t)

p=host/'psp_services.cpp';t=p.read_text();assert 'MessageUtilityState' not in t
t=t.replace('#include "diagnostic_control.hpp"','#include "diagnostic_control.hpp"\n#include "message_dialog.hpp"')
needle='SavedataUtilityState savedata_utility{};'
t=t.replace(needle,needle+'''

// PSP utility message dialog. Parameters use the guest ABI, not host structs.
// Original implementation; size/offset/NID facts are documented in PSPSDK.
struct MessageUtilityState {
    UtilityStatus status{UtilityStatus::None};
    std::uint32_t parameter{}, size{}, previous_buttons{};
    bool release_required{true};
    MessageDialogView view;
};
MessageUtilityState message_utility{};
void message_visibility(bool visible) {
    message_utility.view.visible=visible;
    display_window_set_message_dialog(message_utility.view);
}
void message_finish(psprecomp::Runtime& rt,std::uint32_t button) {
    auto& m=message_utility;
    if(!rt.memory().contains(m.parameter,m.size))throw psprecomp::Error("Message parameter invalidated while active");
    rt.memory().store32(m.parameter+0x1c,0u);
    rt.memory().store32(m.parameter+0x30,0u);
    if(m.size>=580)rt.memory().store32(m.parameter+0x240,button);
    m.status=UtilityStatus::Quit;message_visibility(false);
    std::cerr<<"[msgdialog] complete button="<<button<<" (no savedata bytes modified)\\n";
}
''')
t=t.replace('    savedata_utility = SavedataUtilityState{};','    savedata_utility = SavedataUtilityState{};\n    message_utility = {}; display_window_set_message_dialog({});',1)
idx=t.index('    runtime.register_hle("sceUtility", 0x50C4CD57u,')
hle='''    // Utility system dialogs remain pending until a real/replayed input edge.
    runtime.register_hle("sceUtility", 0x2AD8E239u,
        [](psprecomp::Runtime& rt,psprecomp::AllegrexContext& ctx) {
            const auto fail=[&](std::uint32_t code){ctx.set_gpr(2,code);};
            if(message_utility.status!=UtilityStatus::None){fail(0x80110001u);return;}
            const auto p=ctx.gpr[4];auto& memory=rt.memory();
            if(!p||!memory.contains(p,4)){fail(0x80110004u);return;}
            const auto size=memory.load32(p);
            if((size!=572&&size!=580&&size!=708)||!memory.contains(p,size)){fail(0x80110004u);return;}
            const auto mode=memory.load32(p+0x34),swap=memory.load32(p+8);
            const auto options=size>=580?memory.load32(p+0x23c):0u;
            if(mode>1||swap>1||(options&~0x1b3u)||((options&0x30u)==0x30u)) {fail(0x80110004u);return;}
            MessageUtilityState next;next.parameter=p;next.size=size;next.status=UtilityStatus::Init;
            next.previous_buttons=effective_controller_buttons();
            auto& view=next.view;view.accept_cross=swap==1;
            view.yes_no=(options&0x10u)!=0;view.ok=(options&0x20u)!=0;
            view.cancel=(options&0x80u)==0;view.selected_yes=(options&0x100u)==0;
            if(mode==0) {
                std::ostringstream message;message<<"System error 0x"<<std::hex<<std::uppercase<<std::setfill('0')<<std::setw(8)<<memory.load32(p+0x38);
                view.text=message.str();
            } else {
                view.text=read_fixed_string(memory,p+0x3c,512);
                // The supplied USA title uses ASCII system messages. Unknown
                // text encoding is not silently discarded or reported valid.
                for(unsigned char c:view.text)if((c<32&&c!='\\n'&&c!='\\r'&&c!='\\t')||c>=127){fail(0x80110004u);return;}
            }
            memory.store32(p+0x1c,0);memory.store32(p+0x30,0);
            if(size>=580)memory.store32(p+0x240,0);
            message_utility=std::move(next);
            std::cerr<<"[msgdialog] init size="<<size<<" mode="<<mode<<" options=0x"<<std::hex<<options<<std::dec<<" text="<<message_utility.view.text<<"\\n";
            set_success(ctx);
        });
    runtime.register_hle("sceUtility", 0x9A1C91D7u,
        [](psprecomp::Runtime&,psprecomp::AllegrexContext& ctx) {
            const auto state=message_utility.status;ctx.set_gpr(2,static_cast<std::uint32_t>(state));
            if(state==UtilityStatus::Init){message_utility.status=UtilityStatus::Visible;message_visibility(true);}
            else if(state==UtilityStatus::Finished){message_utility={};display_window_set_message_dialog({});}
        });
    runtime.register_hle("sceUtility", 0x95FC253Bu,
        [](psprecomp::Runtime& rt,psprecomp::AllegrexContext& ctx) {
            auto& m=message_utility;
            if(m.status!=UtilityStatus::Visible){ctx.set_gpr(2,0x80110001u);return;}
            const auto now=effective_controller_buttons(),edge=now&~m.previous_buttons;m.previous_buttons=now;
            if(m.release_required){if(now==0)m.release_required=false;set_success(ctx);return;}
            if(m.view.yes_no){if(edge&0x80u)m.view.selected_yes=true;if(edge&0x20u)m.view.selected_yes=false;}
            if((edge&0x10u)&&m.view.scroll)m.view.scroll--;
            if((edge&0x40u)&&m.view.scroll<512)m.view.scroll++;
            const auto confirm=m.view.accept_cross?0x4000u:0x2000u;
            const auto cancel=m.view.accept_cross?0x2000u:0x4000u;
            if(m.view.cancel&&(edge&cancel))message_finish(rt,3);
            else if((m.view.yes_no||m.view.ok)&&(edge&confirm))message_finish(rt,m.view.yes_no&&!m.view.selected_yes?2:1);
            else message_visibility(true);
            set_success(ctx);
        });
    runtime.register_hle("sceUtility", 0x67AF3428u,
        [](psprecomp::Runtime&,psprecomp::AllegrexContext& ctx) {
            if(message_utility.status!=UtilityStatus::Quit){ctx.set_gpr(2,0x80110001u);return;}
            message_utility.status=UtilityStatus::Finished;message_visibility(false);set_success(ctx);
        });
    runtime.register_hle("sceUtility", 0x4928BD96u,
        [](psprecomp::Runtime& rt,psprecomp::AllegrexContext& ctx) {
            if(message_utility.status!=UtilityStatus::Init&&message_utility.status!=UtilityStatus::Visible){ctx.set_gpr(2,0x80110001u);return;}
            message_finish(rt,0);set_success(ctx);
        });

'''
t=t[:idx]+hle+t[idx:]
# Test implementation follows below, exercising registered production functions.
p.write_text(t)
print('Message dialog host/UI and production HLE installed; no game data replacement')
