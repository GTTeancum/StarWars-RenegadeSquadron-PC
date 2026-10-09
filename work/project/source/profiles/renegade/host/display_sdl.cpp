#include "modern_input008.hpp"
#include "display_window.hpp"
#include "ge_renderer.hpp"
#include "display_ui.hpp"
#include "message_dialog.hpp"
#include "game_font.hpp"
#include <cctype>
#include "psprecomp/common.hpp"
#include <SDL2/SDL.h>
#include <SDL2/SDL_syswm.h>
#include "ge_gpu_backend.hpp"
#include "test_environment010.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <string>
#include <vector>
#include <utility>
namespace vcs { namespace {
namespace ui=renegade::ui;
SDL_Window* window{}; SDL_Renderer* renderer{}; SDL_Texture* texture{}; SDL_GameController* pad{};
unsigned tw{},th{}; bool closed{},focused{},menu_open{};
// Direct presentation: the DX12 GE backend owns the window's swapchain and
// presents each finished frame itself. SDL keeps only the window, events and
// controllers; no SDL renderer exists, so nothing else draws into the window.
bool direct_present{};
// PC replacement for the PSP on-screen keyboard: while the game requests text
// (sceUtilityOsk*), typed keys edit this field instead of reaching the game.
struct TextEntry {
 bool active{},done{},cancelled{};
 std::string title,text;
 std::size_t limit{16};
 std::uint32_t previous_pad{};
} text_entry;
bool inspect_textures{};std::uint32_t inspection_framebuffer{};
int choice=1,hover=1;
std::array<bool,SDL_NUM_SCANCODES> keys{};
// Mouse state for keyboard/mouse play: motion accumulated between samples,
// held buttons, wheel steps turned into one-sample presses.
int mouse_dx=0,mouse_dy=0; std::array<bool,6> mouse_buttons{}; int wheel_up=0,wheel_down=0; bool mouse_moved=false;
bool relative_mouse=false;
// Pad-button bindings for the keyboard/mouse (RENEGADE_KEY_<button>, from the
// settings file [Keyboard]). A binding names an SDL key ("Space", "Left Shift",
// "E"), a mouse button (Mouse1..Mouse5) or the wheel (WheelUp, WheelDown).
struct Binding { SDL_Scancode key=SDL_SCANCODE_UNKNOWN; int mouse=0; int wheel=0; };
constexpr const char* binding_names[18]={"A","B","X","Y","Back","Guide","Start","LS","RS","LB","RB","Up","Down","Left","Right","LT","RT","Pause"};
constexpr const char* binding_defaults[18]={"Space","C","E","Q","Tab","","Escape","Left Shift","V","F","Mouse3","R","G","WheelUp","WheelDown","Mouse2","Mouse1","Escape"};
std::array<Binding,18> bindings{}; bool bindings_loaded=false;
Binding parse_binding(const std::string& text) {
 Binding b; if(text.empty())return b;
 if(text.size()==6&&text.compare(0,5,"Mouse")==0&&text[5]>='1'&&text[5]<='5'){b.mouse=text[5]-'0';return b;}
 if(text=="WheelUp"){b.wheel=1;return b;} if(text=="WheelDown"){b.wheel=-1;return b;}
 b.key=SDL_GetScancodeFromName(text.c_str());
 if(b.key==SDL_SCANCODE_UNKNOWN)std::cerr<<"[display-sdl] unknown key name \""<<text<<"\" in the keyboard settings\n";
 return b;
}
void load_bindings() {
 if(bindings_loaded)return; bindings_loaded=true;
 for(int i=0;i<18;++i){const std::string name=std::string("RENEGADE_KEY_")+binding_names[i];const char* v=std::getenv(name.c_str());bindings[i]=parse_binding(v&&*v?v:binding_defaults[i]);}
}
bool binding_held(const Binding& b) {
 if(b.key!=SDL_SCANCODE_UNKNOWN&&keys[b.key])return true;
 if(b.mouse&&mouse_buttons[b.mouse])return true;
 if(b.wheel>0&&wheel_up>0)return true; if(b.wheel<0&&wheel_down>0)return true;
 return false;
}
void set_relative_mouse(bool on){if(on==relative_mouse||!window)return;relative_mouse=on;SDL_SetRelativeMouseMode(on?SDL_TRUE:SDL_FALSE);}
std::string capture_request;
MessageDialogView message_view;
// Window size requested by settings (any WxH, not only the toolbar presets).
int requested_width=0,requested_height=0; bool requested_fullscreen=false;
// Asura PC applies the user's resolution/fullscreen choice to its window and
// device (Asura_Direct3D_UserOptions); here SDL resizes the window and the
// DX12 swapchain follows the client size. A 0x0 size means the desktop size.
void apply_video_mode(int width,int height,bool fullscreen) {
 if(!window)return;
 if(width<=0||height<=0){SDL_DisplayMode desktop{};const int index=std::max(0,SDL_GetWindowDisplayIndex(window));
  if(SDL_GetDesktopDisplayMode(index,&desktop)==0){width=desktop.w;height=desktop.h;}else{width=1280;height=720;}}
 if(fullscreen){
  SDL_DisplayMode mode{SDL_PIXELFORMAT_UNKNOWN,width,height,0,nullptr};
  SDL_SetWindowDisplayMode(window,&mode);
  if(SDL_SetWindowFullscreen(window,SDL_WINDOW_FULLSCREEN)!=0)std::cerr<<"[display-sdl] fullscreen failed: "<<SDL_GetError()<<"\n";
 }else{
  SDL_SetWindowFullscreen(window,0);
  if(SDL_GetWindowFlags(window)&SDL_WINDOW_MAXIMIZED)SDL_RestoreWindow(window);
  SDL_SetWindowSize(window,width,height+(direct_present?0:ui::toolbar_height));
  SDL_SetWindowPosition(window,SDL_WINDOWPOS_CENTERED,SDL_WINDOWPOS_CENTERED);
 }
 std::cerr<<"[display-sdl] video mode "<<width<<"x"<<height<<(fullscreen?" fullscreen":" windowed")<<"\n";
}
bool on(const char* k){ const char* v=std::getenv(k);return v && *v && std::strcmp(v,"0")!=0; }
void checked(int rc,const char* operation) { if(rc<0)throw psprecomp::Error(std::string(operation)+": "+SDL_GetError()); }
void clear_input() { keys.fill(false); mouse_buttons.fill(false); mouse_dx=mouse_dy=0; wheel_up=wheel_down=0; mouse_moved=false; }
// Small original stroke cells for UI labels. No runtime font asset/dependency.
// Seven rows, most significant five bits are not used; columns read bit 4..0.
std::array<unsigned char,7> glyph(char c) {
 switch(c) {
 case 'A':return {14,17,17,31,17,17,17}; case 'B':return {30,17,17,30,17,17,30};
 case 'C':return {14,17,16,16,16,17,14}; case 'D':return {30,17,17,17,17,17,30};
 case 'E':return {31,16,16,30,16,16,31}; case 'F':return {31,16,16,30,16,16,16};
 case 'G':return {14,17,16,23,17,17,15}; case 'H':return {17,17,17,31,17,17,17};
 case 'I':return {14,4,4,4,4,4,14}; case 'J':return {7,2,2,2,18,18,12};
 case 'K':return {17,18,20,24,20,18,17}; case 'L':return {16,16,16,16,16,16,31};
 case 'M':return {17,27,21,21,17,17,17}; case 'N':return {17,25,25,21,19,19,17};
 case 'O':return {14,17,17,17,17,17,14}; case 'P':return {30,17,17,30,16,16,16};
 case 'Q':return {14,17,17,17,21,18,13}; case 'R':return {30,17,17,30,20,18,17};
 case 'S':return {15,16,16,14,1,1,30}; case 'T':return {31,4,4,4,4,4,4};
 case 'U':return {17,17,17,17,17,17,14}; case 'V':return {17,17,17,17,17,10,4};
 case 'W':return {17,17,17,21,21,21,10}; case 'X':return {17,17,10,4,10,17,17};
 case 'Y':return {17,17,10,4,4,4,4}; case 'Z':return {31,1,2,4,8,16,31};
 case '0':return {14,17,19,21,25,17,14}; case '1':return {4,12,4,4,4,4,14};
 case '2':return {14,17,1,2,4,8,31}; case '3':return {30,1,1,14,1,1,30};
 case '4':return {2,6,10,18,31,2,2}; case '5':return {31,16,16,30,1,1,30};
 case '6':return {14,16,16,30,17,17,14}; case '7':return {31,1,2,4,8,8,8};
 case '8':return {14,17,17,14,17,17,14}; case '9':return {14,17,17,15,1,1,14};
 case '(':return {2,4,8,8,8,4,2}; case ')':return {8,4,2,2,2,4,8};
 case '?':return {14,17,1,2,4,0,4}; case '!':return {4,4,4,4,4,0,4};
 case ',':return {0,0,0,0,6,4,8}; case '\'':return {4,4,8,0,0,0,0};
 case '=':return {0,31,0,31,0,0,0};
 case '-':return {0,0,0,31,0,0,0}; case ':':return {0,4,4,0,4,4,0};
 case '/':return {1,1,2,4,8,16,16}; case '.':return {0,0,0,0,0,6,6};
 default:return {};
 }
}
void text(int x,int y,const std::string& s,SDL_Color color,int scale=2) {
 SDL_SetRenderDrawColor(renderer,color.r,color.g,color.b,255);
 for(char c:s) { const auto rows=glyph(char(std::toupper(static_cast<unsigned char>(c)))); for(int j=0;j<7;++j)for(int i=0;i<5;++i)
  if(rows[j]&(1u<<(4-i))) {SDL_Rect r{x+i*scale,y+j*scale,scale,scale};SDL_RenderFillRect(renderer,&r);} x+=6*scale; }
}
void fill(ui::Rect r,SDL_Color c) {SDL_SetRenderDrawColor(renderer,c.r,c.g,c.b,255);SDL_Rect t{r.x,r.y,r.w,r.h};SDL_RenderFillRect(renderer,&t);}
void apply_choice(int index) {
 if(index<0 || index>=int(ui::resolutions.size()))throw psprecomp::Error("Invalid output-resolution selection");
 choice=hover=index;menu_open=false;clear_input();
 const auto& r=ui::resolutions[index];
 if(SDL_GetWindowFlags(window)&SDL_WINDOW_MAXIMIZED)SDL_RestoreWindow(window);
 SDL_SetWindowSize(window,r.width,r.height+ui::toolbar_height);
 std::cerr<<"[display-sdl] output="<<r.width<<"x"<<r.height<<" toolbar="<<ui::toolbar_height<<" internal=480x272 fallback; HD presentation follows when available\n";
}
void open_menu() { menu_open=true;hover=choice;clear_input(); }
void save_frame(const std::filesystem::path& path) {
 int w=0,h=0;checked(SDL_GetRendererOutputSize(renderer,&w,&h),"capture output size");
 if(w<=0||h<=0||w>16384||h>16384)throw psprecomp::Error("Invalid presentation capture size");
 std::vector<std::uint8_t> rgba(std::size_t(w)*h*4);
 checked(SDL_RenderReadPixels(renderer,nullptr,SDL_PIXELFORMAT_RGBA32,rgba.data(),w*4),"presentation capture");
 if(!path.parent_path().empty())std::filesystem::create_directories(path.parent_path());
 std::ofstream file(path,std::ios::binary|std::ios::trunc);file<<"P6\n"<<w<<" "<<h<<"\n255\n";
 for(std::size_t i=0;i<rgba.size();i+=4)file.write(reinterpret_cast<const char*>(rgba.data()+i),3);
 if(!file)throw psprecomp::Error("Could not save presentation capture: "+path.string());
 std::cerr<<"[display-sdl] captured "<<path<<" ("<<w<<"x"<<h<<")\n";
}
// Original host modal; source framebuffer pixels and game state are unchanged.
std::vector<std::string> wrap_message(const std::string& input, unsigned columns) {
 std::vector<std::string> result; std::string line;
 for(unsigned char byte:input) {
  if(byte=='\r')continue;
  if(byte=='\n'){result.push_back(line);line.clear();continue;}
  const char c=byte=='\t'?' ':char(std::toupper(byte));
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
// Direct GPU presentation has no SDL renderer, so the PSP system message is
// drawn into a transparent RGBA image (same layout and stroke font as
// draw_message_dialog) and composited over the frame by the GPU.
struct Canvas {
 unsigned w,h; std::vector<std::byte>& px;
 void fill(int x,int y,int rw,int rh,SDL_Color c){
  for(int j=std::max(0,y);j<std::min(int(h),y+rh);++j)for(int i=std::max(0,x);i<std::min(int(w),x+rw);++i){
   auto* p=px.data()+(std::size_t(j)*w+i)*4;p[0]=std::byte(c.r);p[1]=std::byte(c.g);p[2]=std::byte(c.b);p[3]=std::byte(c.a);}
 }
 void text(int x,int y,const std::string& s,SDL_Color c,int scale){
  for(char ch:s){const auto rows=glyph(char(std::toupper(static_cast<unsigned char>(ch))));
   for(int j=0;j<7;++j)for(int i=0;i<5;++i)if(rows[j]&(1u<<(4-i)))fill(x+i*scale,y+j*scale,scale,scale,c);x+=6*scale;}
 }
};
// Text entry panel, drawn through fill/text callbacks so the SDL renderer and
// the direct-GPU RGBA canvas share one layout.
template<class Fill,class Text>
void draw_text_entry(int ww,int wh,int top,int scale,Fill&& fill_rect,Text&& draw_text) {
 const int margin=12*scale,panel_width=std::min(ww-24,900),height=58*scale;
 const int x=(ww-panel_width)/2,y=top+std::max(8,(wh-top-height)/2);
 fill_rect(x,y,panel_width,height,SDL_Color{24,31,43,240});
 fill_rect(x,y,panel_width,2,SDL_Color{99,179,225,255});
 draw_text(x+margin,y+10*scale,text_entry.title.empty()?std::string("ENTER TEXT"):text_entry.title,SDL_Color{162,213,245,255},scale);
 const std::string shown=text_entry.text+((SDL_GetTicks()/400)%2?"_":" ");
 fill_rect(x+margin-4,y+24*scale,panel_width-2*margin+8,13*scale,SDL_Color{12,16,24,255});
 draw_text(x+margin,y+27*scale,shown,SDL_Color{238,243,250,255},scale);
 draw_text(x+margin,y+44*scale,"TYPE ON KEYBOARD - ENTER: CONFIRM  ESC: CANCEL",SDL_Color{194,212,233,255},scale);
}
// Menu-styled overlay pieces: the game's fonts and the front end's colours
// (dark translucent page, blue button bars, white lettering). Canvas is the
// 960x544 overlay (2x PSP), so the fonts draw at an exact 2x.
namespace themed {
using renegade::game_font::Face;
constexpr SDL_Color kPage{8,10,16,200},kBarDark{14,70,112,255},kBar{26,132,196,255},kBarEdge{120,200,240,255},kText{240,244,248,255},kDim{176,196,216,255};
void bar(Canvas& c,int x,int y,int w,int h,bool bright){
 c.fill(x,y,w,h,bright?kBar:kBarDark);c.fill(x,y,w,2,kBarEdge);c.fill(x,y+h-2,w,2,kBarEdge);c.fill(x,y,2,h,kBarEdge);c.fill(x+w-2,y,2,h,kBarEdge);
}
void label(Canvas& c,int x,int y,const std::string& s,Face face,SDL_Color col){
 renegade::game_font::draw(c.px,c.w,c.h,x,y,s,face,2,{col.r,col.g,col.b});
}
int width(const std::string& s,Face face){return renegade::game_font::text_width(face,s,2);}
void centred(Canvas& c,int cx,int y,const std::string& s,Face face,SDL_Color col){label(c,cx-width(s,face)/2,y,s,face,col);}
}
bool draw_message_dialog_rgba(std::vector<std::byte>& rgba,unsigned ww,unsigned wh) {
 using namespace themed;
 if(text_entry.active) {
  rgba.assign(std::size_t(ww)*wh*4,std::byte{0});
  Canvas canvas{ww,wh,rgba};
  if(!renegade::game_font::loaded()) {
   draw_text_entry(int(ww),int(wh),0,2,
    [&](int x,int y,int w,int h,SDL_Color c){canvas.fill(x,y,w,h,c);},
    [&](int x,int y,const std::string& s,SDL_Color c,int scale){canvas.text(x,y,s,c,scale);});
   return true;
  }
  // Like the New Profile page: title, a button bar holding the typed name, a prompt line.
  // The game blanks its own display while the name box is up (PSP OSK utility),
  // so the page is painted whole in the front end's dark red.
  canvas.fill(0,0,int(ww),int(wh),SDL_Color{44,10,12,255});
  const int cx=int(ww)/2,panel_w=560,panel_h=190,px=cx-panel_w/2,py=int(wh)/2-panel_h/2;
  canvas.fill(px,py,panel_w,panel_h,kPage);canvas.fill(px,py,panel_w,2,kBarEdge);canvas.fill(px,py+panel_h-2,panel_w,2,kBarEdge);
  centred(canvas,cx,py+18,text_entry.title.empty()?std::string("Enter Name"):text_entry.title,Face::Large,kText);
  const int bar_w=360,bar_h=42,bx=cx-bar_w/2,by=py+72;
  bar(canvas,bx,by,bar_w,bar_h,true);
  const std::string shown=text_entry.text+((SDL_GetTicks()/400)%2?"_":"");
  label(canvas,bx+16,by+(bar_h-renegade::game_font::height(Face::Small,2))/2,shown,Face::Small,kText);
  centred(canvas,cx,py+panel_h-50,"Type a name, then press Enter or A to confirm",Face::Small,kDim);
  centred(canvas,cx,py+panel_h-28,"Esc or B to cancel",Face::Small,kDim);
  return true;
 }
 if(!message_view.visible)return false;
 rgba.assign(std::size_t(ww)*wh*4,std::byte{0});
 Canvas canvas{ww,wh,rgba};
 if(renegade::game_font::loaded()) {
  // Like the Load Successful page: message lines centred, Yes/No or Continue bars.
  std::vector<std::string> lines;
  { std::string line; const unsigned max_w=unsigned(ww)-160;
    std::string word; std::string in=message_view.text+" ";
    for(char ch:in){ if(ch=='\r')continue; if(ch==' '||ch=='\n'){ const std::string trial=line.empty()?word:line+" "+word;
      if(width(trial,Face::Small)>int(max_w)&&!line.empty()){lines.push_back(line);line=word;} else line=trial; word.clear(); if(ch=='\n'){lines.push_back(line);line.clear();} } else word.push_back(ch);}
    if(!line.empty())lines.push_back(line); }
  const int lh=renegade::game_font::height(Face::Small,2)+4;
  const int buttons=message_view.yes_no?2:(message_view.ok||message_view.cancel?1:0);
  const int panel_h=60+int(lines.size())*lh+(buttons?70:30),cx=int(ww)/2,py=int(wh)/2-panel_h/2;
  canvas.fill(0,py,int(ww),panel_h,kPage);canvas.fill(0,py,int(ww),2,kBarEdge);canvas.fill(0,py+panel_h-2,int(ww),2,kBarEdge);
  int y=py+28;
  for(const std::string& l:lines){centred(canvas,cx,y,l,Face::Small,kText);y+=lh;}
  y+=16;
  if(message_view.yes_no){
   const int bw=200,bh=42,gap=40;
   bar(canvas,cx-gap/2-bw,y,bw,bh,message_view.selected_yes);centred(canvas,cx-gap/2-bw/2,y+(bh-renegade::game_font::height(Face::Small,2))/2,"Yes",Face::Small,kText);
   bar(canvas,cx+gap/2,y,bw,bh,!message_view.selected_yes);centred(canvas,cx+gap/2+bw/2,y+(bh-renegade::game_font::height(Face::Small,2))/2,"No",Face::Small,kText);
  } else if(buttons){
   const int bw=240,bh=42;bar(canvas,cx-bw/2,y,bw,bh,true);
   centred(canvas,cx,y+(bh-renegade::game_font::height(Face::Small,2))/2,message_view.ok?"Continue":"Back",Face::Small,kText);
  }
  std::string hint=message_view.accept_cross?"A / Enter select":"B / Enter select";
  if(message_view.cancel)hint+=message_view.accept_cross?"     B / Backspace back":"     A / Backspace back";
  label(canvas,int(ww)-width(hint,Face::Small)-24,py+panel_h-renegade::game_font::height(Face::Small,2)-10,hint,Face::Small,kDim);
  return true;
 }
 const int scale=2;
 const int margin=12*scale,panel_width=std::min(int(ww)-24,900),line_height=10*scale;
 const unsigned columns=unsigned(std::max(1,(panel_width-2*margin)/(6*scale)));
 const auto lines=wrap_message(message_view.text,columns);
 const unsigned capacity=unsigned(std::max(1,(int(wh)-16-64*scale)/line_height));
 const unsigned shown=std::min(capacity,unsigned(lines.size()));
 const unsigned offset=std::min(message_view.scroll,unsigned(lines.size())-shown);
 const int height=int(shown)*line_height+64*scale;
 const int x=(int(ww)-panel_width)/2,y=std::max(8,(int(wh)-height)/2);
 canvas.fill(x,y,panel_width,height,{24,31,43,235});
 canvas.fill(x,y,panel_width,2,{99,179,225,255});
 canvas.text(x+margin,y+10*scale,"PSP SYSTEM MESSAGE",{162,213,245,255},scale);
 for(unsigned i=0;i<shown;++i)canvas.text(x+margin,y+25*scale+int(i)*line_height,lines[offset+i],{238,243,250,255},scale);
 int by=y+25*scale+int(shown)*line_height;
 if(lines.size()>shown)canvas.text(x+margin,by,"UP/DOWN TO SCROLL",{162,181,206,255},scale);
 by+=12*scale;
 if(message_view.yes_no){canvas.text(x+margin,by,message_view.selected_yes?"(YES)    NO":" YES    (NO)",{133,215,247,255},scale);by+=11*scale;}
 std::string hint;
 if(message_view.yes_no||message_view.ok)hint=message_view.accept_cross?"CROSS: CONFIRM":"CIRCLE: CONFIRM";
 if(message_view.cancel){if(!hint.empty())hint+="  ";hint+=message_view.accept_cross?"CIRCLE: BACK":"CROSS: BACK";}
 if(hint.empty())hint="WAITING FOR APPLICATION";
 canvas.text(x+margin,by,hint,{194,212,233,255},scale);
 return true;
}
void render(bool present=true) {
 if(!window || !renderer)return;
 checked(SDL_RenderSetViewport(renderer,nullptr),"viewport reset");
 checked(SDL_RenderSetScale(renderer,1,1),"scale reset");
 checked(SDL_SetRenderDrawColor(renderer,0,0,0,255),"clear color");checked(SDL_RenderClear(renderer),"clear");
 int ow=0,oh=0,ww=0,wh=0;checked(SDL_GetRendererOutputSize(renderer,&ow,&oh),"output size");SDL_GetWindowSize(window,&ww,&wh);
 if(ww<=0||wh<=0||ow<=0||oh<=0)return;
 // Physical-pixel content rectangle below toolbar, preserving authored aspect.
 const int top=std::min(oh,int((std::int64_t(ui::toolbar_height)*oh+wh-1)/wh));
 if(texture) {auto r=ui::fit(ow,oh,int(tw),int(th),top);SDL_Rect dst{r.x,r.y,r.w,r.h};
  if(r.w&&r.h)checked(SDL_RenderCopy(renderer,texture,nullptr,&dst),"frame copy");}
 // UI uses window coordinates: clicks remain correct on high-DPI outputs.
 checked(SDL_RenderSetScale(renderer,float(ow)/ww,float(oh)/wh),"UI scale");
 fill({0,0,ww,ui::toolbar_height},{27,32,42,255});
 fill({0,ui::toolbar_height-1,ww,1},{70,82,99,255});
 text(12,13,"OUTPUT SIZE",{197,207,219,255});
 fill(ui::selector,menu_open?SDL_Color{51,73,98,255}:SDL_Color{42,51,66,255});
 SDL_SetRenderDrawColor(renderer,92,151,202,255);SDL_Rect border{ui::selector.x,ui::selector.y,ui::selector.w,ui::selector.h};SDL_RenderDrawRect(renderer,&border);
 const auto& chosen=ui::resolutions[choice];
 const bool exact=ww==chosen.width && wh==chosen.height+ui::toolbar_height;
 const std::string label=exact?chosen.label:(std::to_string(ww)+" X "+std::to_string(std::max(0,wh-ui::toolbar_height))+" CUSTOM");
 text(ui::selector.x+10,ui::selector.y+7,label,{231,239,250,255});
 const int ax=ui::selector.x+ui::selector.w-17,ay=ui::selector.y+12;
 SDL_SetRenderDrawColor(renderer,183,216,245,255);for(int j=0;j<5;++j)SDL_RenderDrawLine(renderer,ax+j,ay+j,ax+8-j,ay+j);
 if(ww>=790)text(468,16,"INTERNAL "+std::to_string(tw)+" X "+std::to_string(th)+" - F9 TEXTURE - ALT R SIZE",{151,167,189,255},1);
 if(inspect_textures) {
  const auto lines=ge_texture_inspection_lines(inspection_framebuffer);
  fill({8,ui::toolbar_height+8,std::min(ww-16,950),int(lines.size())*15+12},{18,23,30,255});
  int y=ui::toolbar_height+14;for(const auto& line:lines){text(14,y,line,{229,236,244,255},1);y+=15;}
 }
 draw_message_dialog(ww,wh);
 if(text_entry.active) {
  const int scale=ww>=800?2:1;
  draw_text_entry(ww,wh,ui::toolbar_height,scale,
   [&](int x,int y,int w,int h,SDL_Color c){fill({x,y,w,h},c);},
   [&](int x,int y,const std::string& s,SDL_Color c,int sc){text(x,y,s,c,sc);});
 }
 if(menu_open) {
  fill({ui::selector.x,ui::toolbar_height,ui::selector.w,int(ui::resolutions.size())*ui::row_height},{28,36,48,255});
  for(int i=0;i<int(ui::resolutions.size());++i) {
   const int y=ui::toolbar_height+i*ui::row_height;
   if(i==hover)fill({ui::selector.x,y,ui::selector.w,ui::row_height},{47,77,107,255});
   if(i==choice)fill({ui::selector.x+4,y+9,3,12},{100,200,235,255});
   text(ui::selector.x+12,y+8,ui::resolutions[i].label,{232,239,247,255});
  }
 }
 checked(SDL_RenderSetScale(renderer,1,1),"UI scale reset");
 // Read the rendered pixels BEFORE swap/present; no visual synthesis.
 if(!capture_request.empty()){auto path=std::exchange(capture_request,{});save_frame(path);}
 if(present)SDL_RenderPresent(renderer);
}
void poll(){if(!window)return;bool dirty=false;SDL_Event e;while(SDL_PollEvent(&e)) {
 if(e.type==SDL_QUIT){closed=true;continue;}
 if(e.type==SDL_WINDOWEVENT && e.window.windowID==SDL_GetWindowID(window)) {
  if(e.window.event==SDL_WINDOWEVENT_CLOSE)closed=true;
  if(e.window.event==SDL_WINDOWEVENT_FOCUS_LOST){focused=false;menu_open=false;clear_input();dirty=true;}
  if(e.window.event==SDL_WINDOWEVENT_FOCUS_GAINED){focused=true;clear_input();}
  if(e.window.event==SDL_WINDOWEVENT_SIZE_CHANGED || e.window.event==SDL_WINDOWEVENT_EXPOSED)dirty=true;
 }
 if(text_entry.active && !text_entry.done) {
  if(e.type==SDL_TEXTINPUT) {
   for(const char* c=e.text.text;*c;++c) {
    const unsigned char ch=static_cast<unsigned char>(*c);
    if(ch>=32&&ch<127&&text_entry.text.size()<text_entry.limit)text_entry.text.push_back(char(ch));
   }
   dirty=true;continue;
  }
  if(e.type==SDL_KEYDOWN) {
   const auto sc=e.key.keysym.scancode;
   if(sc==SDL_SCANCODE_BACKSPACE&&!text_entry.text.empty())text_entry.text.pop_back();
   else if(sc==SDL_SCANCODE_RETURN||sc==SDL_SCANCODE_KP_ENTER)text_entry.done=true;
   else if(sc==SDL_SCANCODE_ESCAPE){text_entry.done=true;text_entry.cancelled=true;}
   dirty=true;continue;
  }
  if(e.type==SDL_KEYUP)continue;
 }
 if(e.type==SDL_MOUSEBUTTONDOWN && e.button.windowID==SDL_GetWindowID(window) && e.button.button==SDL_BUTTON_LEFT) {
  if(ui::inside(ui::selector,e.button.x,e.button.y)){if(menu_open)menu_open=false;else open_menu();clear_input();dirty=true;continue;}
  if(menu_open){const int row=ui::selected_row(e.button.x,e.button.y);if(row>=0)apply_choice(row);else{menu_open=false;clear_input();}dirty=true;continue;}
 }
 if(e.type==SDL_MOUSEMOTION && e.motion.windowID==SDL_GetWindowID(window) && menu_open){const int row=ui::selected_row(e.motion.x,e.motion.y);if(row>=0){hover=row;dirty=true;}}
 if(e.type==SDL_MOUSEMOTION && e.motion.windowID==SDL_GetWindowID(window) && focused && !menu_open){mouse_dx+=e.motion.xrel;mouse_dy+=e.motion.yrel;if(e.motion.xrel||e.motion.yrel)mouse_moved=true;}
 if((e.type==SDL_MOUSEBUTTONDOWN||e.type==SDL_MOUSEBUTTONUP) && e.button.windowID==SDL_GetWindowID(window) && e.button.button>=1 && e.button.button<=5 && !menu_open)mouse_buttons[e.button.button]=e.type==SDL_MOUSEBUTTONDOWN;
 if(e.type==SDL_MOUSEWHEEL && focused){if(e.wheel.y>0)wheel_up+=e.wheel.y;else if(e.wheel.y<0)wheel_down-=e.wheel.y;}
 if((e.type==SDL_KEYDOWN || e.type==SDL_KEYUP) && e.key.windowID==SDL_GetWindowID(window)) {
  const bool down=e.type==SDL_KEYDOWN;const auto sc=e.key.keysym.scancode;
  if(!focused)continue;
  // The output-size selector and texture inspector are drawn by the SDL
  // renderer, which does not exist while the GPU presents directly.
  if(direct_present && down && (sc==SDL_SCANCODE_F9 || sc==SDL_SCANCODE_F12 ||
     (sc==SDL_SCANCODE_R && (e.key.keysym.mod&KMOD_ALT))))continue;
  if(down && !e.key.repeat && sc==SDL_SCANCODE_F9) {
   inspect_textures=!inspect_textures;ge_set_texture_inspection(inspect_textures);dirty=true;continue;
  }
  if(down && !e.key.repeat && sc==SDL_SCANCODE_F12) {
   const char* d=std::getenv("RENEGADE_SCREENSHOT_DIRECTORY");
   if(d&&*d)capture_request=(std::filesystem::path(d)/("presentation-"+std::to_string(SDL_GetTicks64())+".ppm")).string();
   dirty=true;continue;
  }
  if(down && !e.key.repeat && sc==SDL_SCANCODE_R && (e.key.keysym.mod&KMOD_ALT)){if(menu_open){menu_open=false;clear_input();}else open_menu();dirty=true;continue;}
  if(menu_open) {
   if(down && !e.key.repeat) {
    if(sc==SDL_SCANCODE_UP)hover=(hover+int(ui::resolutions.size())-1)%int(ui::resolutions.size());
    if(sc==SDL_SCANCODE_DOWN)hover=(hover+1)%int(ui::resolutions.size());
    if(sc==SDL_SCANCODE_RETURN || sc==SDL_SCANCODE_KP_ENTER)apply_choice(hover);
    if(sc==SDL_SCANCODE_ESCAPE){menu_open=false;clear_input();}
   }
   dirty=true;continue;
  }
  if(sc>=0 && sc<SDL_NUM_SCANCODES)keys[sc]=down;
  // Escape is the pause button in play (RENEGADE_KEY_Pause); Alt+F4 or the
  // main menu's Quit Game end the session.
 }
 if(e.type==SDL_CONTROLLERDEVICEADDED && !pad && SDL_IsGameController(e.cdevice.which))pad=SDL_GameControllerOpen(e.cdevice.which);
 if(e.type==SDL_CONTROLLERDEVICEREMOVED && pad && SDL_JoystickInstanceID(SDL_GameControllerGetJoystick(pad))==e.cdevice.which){SDL_GameControllerClose(pad);pad=nullptr;for(int i=0;i<SDL_NumJoysticks();++i)if(SDL_IsGameController(i)){pad=SDL_GameControllerOpen(i);if(pad)break;}}
 }
 if(dirty)render();
}
HostInputState sample(){poll();HostInputState s;if(!window||!focused||menu_open||closed||text_entry.active)return s;
 load_bindings();
 // PSP buttons for the menus and the original layout: arrows and Enter/Space
 // for Cross, Backspace/X for Circle, plus the bound pause key for Start.
 const std::pair<SDL_Scancode,unsigned> mapping[]={
 {SDL_SCANCODE_TAB,1},{SDL_SCANCODE_RETURN,0x4000},{SDL_SCANCODE_KP_ENTER,0x4000},{SDL_SCANCODE_UP,0x10},{SDL_SCANCODE_RIGHT,0x20},{SDL_SCANCODE_DOWN,0x40},{SDL_SCANCODE_LEFT,0x80},
 {SDL_SCANCODE_Q,0x100},{SDL_SCANCODE_R,0x200},{SDL_SCANCODE_E,0x1000},{SDL_SCANCODE_C,0x2000},{SDL_SCANCODE_SPACE,0x4000},{SDL_SCANCODE_Z,0x4000},{SDL_SCANCODE_X,0x2000},{SDL_SCANCODE_BACKSPACE,0x2000},{SDL_SCANCODE_F,0x8000}};
 for(auto [k,b]:mapping)if(keys[k])s.buttons|=b;
 if(binding_held(bindings[17]))s.buttons|=8; // Start
 if(mouse_buttons[1])s.buttons|=0x4000; // click = Cross in menus
 s.analog_x=keys[SDL_SCANCODE_A]==keys[SDL_SCANCODE_D]?128:keys[SDL_SCANCODE_A]?0:255;
 s.analog_y=keys[SDL_SCANCODE_W]==keys[SDL_SCANCODE_S]?128:keys[SDL_SCANCODE_W]?0:255;
 if(pad){const std::pair<SDL_GameControllerButton,unsigned> buttons[]={{SDL_CONTROLLER_BUTTON_BACK,1},{SDL_CONTROLLER_BUTTON_START,8},{SDL_CONTROLLER_BUTTON_DPAD_UP,0x10},{SDL_CONTROLLER_BUTTON_DPAD_RIGHT,0x20},{SDL_CONTROLLER_BUTTON_DPAD_DOWN,0x40},{SDL_CONTROLLER_BUTTON_DPAD_LEFT,0x80},{SDL_CONTROLLER_BUTTON_LEFTSHOULDER,0x100},{SDL_CONTROLLER_BUTTON_RIGHTSHOULDER,0x200},{SDL_CONTROLLER_BUTTON_Y,0x1000},{SDL_CONTROLLER_BUTTON_B,0x2000},{SDL_CONTROLLER_BUTTON_A,0x4000},{SDL_CONTROLLER_BUTTON_X,0x8000}};for(auto [b,v]:buttons)if(SDL_GameControllerGetButton(pad,b))s.buttons|=v;
  const int x=SDL_GameControllerGetAxis(pad,SDL_CONTROLLER_AXIS_LEFTX),y=SDL_GameControllerGetAxis(pad,SDL_CONTROLLER_AXIS_LEFTY);if(std::abs(x)>7000)s.analog_x=static_cast<std::uint8_t>((x+32768)/256);if(std::abs(y)>7000)s.analog_y=static_cast<std::uint8_t>((y+32768)/256);
 }
 return s;
}
} // namespace
bool display_window_enabled(){return on("PSPRECOMP_WINDOW");}
void display_window_set_message_dialog(const MessageDialogView& view) {
 message_view=view; if(message_view.text.size()>512)message_view.text.resize(512); render();
}
MessageDialogView display_window_message_dialog() { return message_view; }
void display_window_begin_text_entry(const std::string& title,const std::string& initial,std::size_t limit) {
 text_entry=TextEntry{};
 text_entry.active=true;text_entry.title=title;text_entry.limit=std::max<std::size_t>(1,limit);
 text_entry.text=initial.substr(0,text_entry.limit);
 if(window){
  SDL_StartTextInput();
  text_entry.previous_pad=0xFFFFFFFFu;  // ignore buttons already held when the dialog opens
 } else {
  // No window (headless replays/tests): accept RENEGADE_OSK_TEXT or the suggested text.
  if(const char* v=std::getenv("RENEGADE_OSK_TEXT"))text_entry.text=std::string(v).substr(0,text_entry.limit);
  text_entry.done=true;
 }
 std::cerr<<"[text-entry] begin title=\""<<title<<"\" initial=\""<<initial<<"\" limit="<<limit<<"\n";
 render();
}
bool display_window_text_entry_result(std::string& text,bool& cancelled) {
 if(!text_entry.active)return false;
 poll();
 if(!text_entry.done&&pad) {
  // Controller: A/Start confirm the shown text, B cancels.
  std::uint32_t now=0;
  if(SDL_GameControllerGetButton(pad,SDL_CONTROLLER_BUTTON_A))now|=1u;
  if(SDL_GameControllerGetButton(pad,SDL_CONTROLLER_BUTTON_START))now|=2u;
  if(SDL_GameControllerGetButton(pad,SDL_CONTROLLER_BUTTON_B))now|=4u;
  const std::uint32_t edge=text_entry.previous_pad==0xFFFFFFFFu?0u:(now&~text_entry.previous_pad);
  text_entry.previous_pad=now;
  if(edge&3u)text_entry.done=true;
  else if(edge&4u){text_entry.done=true;text_entry.cancelled=true;}
 }
 if(window)render();
 if(!text_entry.done)return false;
 text=text_entry.text;cancelled=text_entry.cancelled;
 return true;
}
void display_window_end_text_entry() {
 if(text_entry.active&&window)SDL_StopTextInput();
 text_entry=TextEntry{};
 clear_input();
 if(window)render();
}
// RGBA overlay of the current PSP system message for direct GPU presentation.
bool display_window_dialog_overlay(std::vector<std::byte>& rgba,unsigned& width,unsigned& height) {
 // RENEGADE_DIALOG_OVERLAY_TEST=1 draws it without a window, for GPU captures.
 static const bool headless_test=on("RENEGADE_DIALOG_OVERLAY_TEST");
 if(!direct_present&&!headless_test)return false;
 width=960;height=544;
 if(headless_test&&!text_entry.active&&std::string(std::getenv("RENEGADE_DIALOG_OVERLAY_TEST"))=="text") {
  // Test-only sample of the PC text entry box.
  text_entry.active=true;text_entry.title="NEW PROFILE NAME";text_entry.text="Col Serra";
  const bool drawn=draw_message_dialog_rgba(rgba,width,height);
  text_entry=TextEntry{};
  return drawn;
 }
 if(headless_test&&!message_view.visible) {
  // Test-only sample message so the overlay can be captured without a guest dialog.
  const MessageDialogView saved=message_view;
  message_view.visible=true;message_view.yes_no=true;message_view.cancel=true;
  message_view.text="Overlay test. Do you want to save your progress?";
  const bool drawn=draw_message_dialog_rgba(rgba,width,height);
  message_view=saved;
  return drawn;
 }
 return draw_message_dialog_rgba(rgba,width,height);
}
void display_window_start(){if(!display_window_enabled() || window)return;
 inspect_textures=on("RENEGADE_TEXTURE_INSPECT");ge_set_texture_inspection(inspect_textures);
 choice=1; if(auto v=std::getenv("PSPRECOMP_WINDOW_SCALE")){if(std::strlen(v)!=1||*v<'1'||*v>'4')throw psprecomp::Error("PSPRECOMP_WINDOW_SCALE must be 1, 2, 3, or 4");choice=*v-'1';}
 if(auto v=std::getenv("RENEGADE_OUTPUT_RESOLUTION")){
  choice=ui::parse_resolution(v);
  if(choice<0){int w=0,h=0;char tail=0;
   if(std::strcmp(v,"desktop")==0){requested_width=requested_height=0;}
   else if(std::sscanf(v,"%dx%d%c",&w,&h,&tail)==2&&w>=480&&h>=272&&w<=7680&&h<=4320){requested_width=w;requested_height=h;}
   else throw psprecomp::Error("Unsupported RENEGADE_OUTPUT_RESOLUTION; use WIDTHxHEIGHT (480x272 up to 7680x4320) or desktop");
   choice=4;}
  else{requested_width=ui::resolutions[choice].width;requested_height=ui::resolutions[choice].height;}
 }
 requested_fullscreen=on("RENEGADE_FULLSCREEN");
 checked(SDL_InitSubSystem(SDL_INIT_VIDEO|SDL_INIT_GAMECONTROLLER),"SDL video");
 try {
  auto res=ui::resolutions[choice];
  if(requested_width>0){res.width=requested_width;res.height=requested_height;}
  const char* direct_setting=std::getenv("RENEGADE_DIRECT_PRESENT");
  direct_present=ge_gpu_backend_active() && !(direct_setting && std::strcmp(direct_setting,"0")==0);
  const int toolbar=direct_present?0:ui::toolbar_height;
  window=SDL_CreateWindow("Renegade Squadron",SDL_WINDOWPOS_UNDEFINED,SDL_WINDOWPOS_UNDEFINED,res.width,res.height+toolbar,SDL_WINDOW_RESIZABLE|SDL_WINDOW_ALLOW_HIGHDPI);
  if(!window)throw psprecomp::Error(std::string("SDL window: ")+SDL_GetError());
  SDL_SetWindowMinimumSize(window,480,272+toolbar);
  if(direct_present) {
   SDL_SysWMinfo info;SDL_VERSION(&info.version);
   if(!SDL_GetWindowWMInfo(window,&info))throw psprecomp::Error(std::string("SDL window handle: ")+SDL_GetError());
#if defined(_WIN32)
   ge_gpu_backend_set_native_window(info.info.win.window);
#endif
   focused=(SDL_GetWindowFlags(window)&SDL_WINDOW_INPUT_FOCUS)!=0;closed=false;menu_open=false;hover=choice;clear_input();
   for(int i=0;i<SDL_NumJoysticks();++i)if(SDL_IsGameController(i)){pad=SDL_GameControllerOpen(i);if(pad)break;}
   std::cerr<<"[display-sdl] direct GPU presentation "<<res.width<<"x"<<res.height<<"; SDL renderer disabled\n";
   if(requested_fullscreen||(requested_width==0&&std::getenv("RENEGADE_OUTPUT_RESOLUTION")))apply_video_mode(requested_width,requested_height,requested_fullscreen);
   return;
  }
  renderer=SDL_CreateRenderer(window,-1,SDL_RENDERER_ACCELERATED);
  if(!renderer)renderer=SDL_CreateRenderer(window,-1,SDL_RENDERER_SOFTWARE);
  if(!renderer)throw psprecomp::Error(std::string("SDL renderer: ")+SDL_GetError());
  focused=(SDL_GetWindowFlags(window)&SDL_WINDOW_INPUT_FOCUS)!=0;closed=false;menu_open=false;hover=choice;clear_input();
  for(int i=0;i<SDL_NumJoysticks();++i)if(SDL_IsGameController(i)){pad=SDL_GameControllerOpen(i);if(pad)break;}
  render();std::cerr<<"[display-sdl] output selector active below title bar; initial guest framebuffer=480x272; HD presentation follows when available\n";
 } catch(...) {display_window_shutdown();throw;}
}
void display_window_set_status(const char* s){if(window){const std::string title=std::string("Renegade Squadron | ")+(s?s:"native PSPRecomp");SDL_SetWindowTitle(window,title.c_str());}}
void display_window_present_rgba(std::span<const std::byte> rgba,std::uint32_t w,std::uint32_t h){if(!display_window_enabled())return;display_window_start();poll();if(direct_present)return;if(!w||!h||w>4096||h>4096||rgba.size()<std::size_t(w)*h*4)throw psprecomp::Error("Invalid SDL frame dimensions");
 if(!texture||tw!=w||th!=h){if(texture)SDL_DestroyTexture(texture);texture=nullptr;texture=SDL_CreateTexture(renderer,SDL_PIXELFORMAT_RGBA32,SDL_TEXTUREACCESS_STREAMING,w,h);if(!texture)throw psprecomp::Error(SDL_GetError());tw=w;th=h;checked(SDL_SetTextureBlendMode(texture,SDL_BLENDMODE_NONE),"frame blending");checked(SDL_SetTextureScaleMode(texture,SDL_ScaleModeNearest),"nearest output scaling");}
 checked(SDL_UpdateTexture(texture,nullptr,rgba.data(),w*4),"frame upload");render();
}
void display_window_present(const psprecomp::GuestMemory& m,const FramebufferDescription& d){
 inspection_framebuffer=d.address;
 if(!display_window_enabled()||!d.address)return;
 if(direct_present){display_window_start();poll();return;}
 const auto* enabled=std::getenv("RENEGADE_HD_PRESENT");
 if(enabled&&std::string(enabled)=="1")if(auto rgb=ge_hd_frame_rgb(d.address,d.pixel_format);!rgb.empty()){
  const auto* fxaa=std::getenv("RENEGADE_FXAA");const bool smooth=fxaa&&std::string(fxaa)=="1";
  if(smooth)rgb=ge_hd_frame_fxaa_rgb(d.address,d.pixel_format);
  std::vector<std::byte> rgba(std::size_t(1280)*720*4);
  for(std::size_t i=0,j=0;i<rgb.size();i+=3,j+=4){rgba[j]=std::byte(rgb[i]);rgba[j+1]=std::byte(rgb[i+1]);rgba[j+2]=std::byte(rgb[i+2]);rgba[j+3]=std::byte{255};}
  static bool reported=false;if(!reported){std::cerr<<"[display-sdl] internal=1280x720 fxaa="<<smooth<<" guest_vram_preserved=1\n";reported=true;}
  display_window_present_rgba(rgba,1280,720);return;
 }
 display_window_present_rgba(decode_framebuffer_rgba(m,d),d.width,d.height);
}
void display_window_set_aspect_lock(bool)noexcept{} // All frames preserve authored aspect; no widescreen game patch.
void display_window_present_gpu_rgba(std::span<const std::byte> rgba,std::uint32_t width,std::uint32_t height,std::uint32_t framebuffer) {
 inspection_framebuffer=framebuffer;
 if(!display_window_enabled())return;
 if(direct_present){poll();return;}
 if(on("RENEGADE_FXAA")) {
  const auto filtered=ge_fxaa_gpu_rgba(framebuffer,width,height,rgba);
  display_window_present_rgba(filtered,width,height);
 }else display_window_present_rgba(rgba,width,height);
}
std::uint32_t display_window_buttons(){return sample().buttons;}
void display_window_analog(std::uint8_t& x,std::uint8_t& y){auto s=sample();x=s.analog_x;y=s.analog_y;}
HostInputState display_window_input(){return sample();}
void display_window_inject_text(const std::string& typed){
 // Diagnostics: feed the text-entry box as if typed ({enter} confirms, {esc} cancels, {bs} deletes).
 if(!text_entry.active||text_entry.done)return;
 for(std::size_t i=0;i<typed.size();++i){
  if(typed.compare(i,7,"{enter}")==0){text_entry.done=true;i+=6;continue;}
  if(typed.compare(i,5,"{esc}")==0){text_entry.done=true;text_entry.cancelled=true;i+=4;continue;}
  if(typed.compare(i,4,"{bs}")==0){if(!text_entry.text.empty())text_entry.text.pop_back();i+=3;continue;}
  const unsigned char ch=static_cast<unsigned char>(typed[i]);
  if(ch>=32&&ch<127&&text_entry.text.size()<text_entry.limit)text_entry.text.push_back(char(ch));
 }
}
void display_window_set_fonts(const std::filesystem::path& fonts_asr){
 if(!renegade::game_font::load(fonts_asr))std::cerr<<"[display-sdl] game fonts unavailable; overlays use the built-in lettering\n";
}
bool display_window_close_requested(){poll();
 // Hide and capture the cursor while the keyboard/mouse drives play.
 set_relative_mouse(window&&focused&&!menu_open&&!text_entry.active&&!message_view.visible&&renegade::input008::keyboard_mouse_active());
 return closed;}
void display_window_request_close(){closed=true;}
void display_window_apply_video(int width,int height,bool fullscreen){apply_video_mode(width,height,fullscreen);}
void display_window_shutdown(){if(direct_present){ge_gpu_backend_set_native_window(nullptr);direct_present=false;}if(pad)SDL_GameControllerClose(pad);pad=nullptr;if(texture)SDL_DestroyTexture(texture);texture=nullptr;if(renderer)SDL_DestroyRenderer(renderer);renderer=nullptr;if(window)SDL_DestroyWindow(window);window=nullptr;tw=th=0;closed=focused=menu_open=false;capture_request.clear();clear_input();SDL_QuitSubSystem(SDL_INIT_GAMECONTROLLER|SDL_INIT_VIDEO);}
DisplayWindowSurface display_window_surface(){DisplayWindowSurface s;int w=0,h=0;if(window)SDL_GetWindowSize(window,&w,&h);s.width=w;s.height=h;return s;}
// Regression entry used by a separate executable. Exercises this production
// window, rendering, and event path; never installs or patches guest game code.
bool run_renegade_display_tests(std::string& error) {
 unsigned checks=0;
 auto check=[&](bool ok,const char* message){++checks;if(!ok)throw psprecomp::Error(message);};
 auto event=[&](SDL_Event e){check(SDL_PushEvent(&e)==1,"SDL event injection failed");poll();};
 auto focus=[&](bool yes){SDL_Event e{};e.type=SDL_WINDOWEVENT;e.window.windowID=SDL_GetWindowID(window);e.window.event=yes?SDL_WINDOWEVENT_FOCUS_GAINED:SDL_WINDOWEVENT_FOCUS_LOST;event(e);};
 auto key=[&](SDL_Scancode sc,bool down=true,Uint16 mod=0){SDL_Event e{};e.type=down?SDL_KEYDOWN:SDL_KEYUP;e.key.windowID=SDL_GetWindowID(window);e.key.keysym.scancode=sc;e.key.keysym.mod=mod;event(e);};
 auto click=[&](int x,int y){SDL_Event e{};e.type=SDL_MOUSEBUTTONDOWN;e.button.windowID=SDL_GetWindowID(window);e.button.button=SDL_BUTTON_LEFT;e.button.x=x;e.button.y=y;event(e);};
 try {
  // Geometric cases, including empty/minimized and very large arithmetic.
  check(ui::parse_resolution("960x544")==1,"resolution parse");
  for(auto bad:{"", "99999x99999", "0x0", "-1x272", "960x544junk", " 960x544", "960X544"})check(ui::parse_resolution(bad)==-1,"malformed resolution accepted");
  check(ui::fit(0,0,480,272).w==0,"zero output geometry");
  check(ui::fit(960,40,480,272).h==0,"toolbar-only output geometry");
  check(ui::fit(960,544,0,272).w==0,"zero source geometry");
  const auto huge=ui::fit(1000000000,1000000000,480,272);check(huge.w>0 && huge.h>0,"64-bit aspect math");
  for(int ww:{480,640,960,1024,1280,1440,1920})for(int hh:{312,400,584,760,856,1120,1128}){
   auto r=ui::fit(ww,hh,480,272);check(r.x>=0 && r.y>=40 && r.w>=0 && r.h>=0 && r.x+r.w<=ww && r.y+r.h<=hh,"aspect fit bounds");
   check(std::abs(std::int64_t(r.w)*272-std::int64_t(r.h)*480)<=480,"aspect fit rounding");
  }
  check(ui::selected_row(162,39)==-1,"popup top bound");check(ui::selected_row(161,40)==-1,"popup left bound");
  check(ui::selected_row(444,40)==-1,"popup right bound");check(ui::selected_row(163,220)==-1,"popup bottom bound");
  display_window_shutdown();renegade::test010::set_environment("PSPRECOMP_WINDOW","0");display_window_start();check(!window,"disabled display created window");
  check(display_window_input().buttons==0,"headless buttons");
  renegade::test010::set_environment("PSPRECOMP_WINDOW","1");renegade::test010::set_environment("RENEGADE_OUTPUT_RESOLUTION","bogus");
  bool rejected=false;try{display_window_start();}catch(const psprecomp::Error&){rejected=true;}check(rejected&&!window,"bad setting did not fail cleanly");
  renegade::test010::set_environment("RENEGADE_OUTPUT_RESOLUTION","960x544");
  for(int lifecycle=0;lifecycle<2;++lifecycle) {
   display_window_start();focus(true);check(!closed&&!menu_open,"window lifecycle reset");
   display_window_set_status("UI TEST");check(std::string(SDL_GetWindowTitle(window))=="Renegade Squadron | UI TEST","status lost game title");
   auto surface=display_window_surface();check(surface.width==960&&surface.height==584,"default 2x output plus toolbar");
   std::vector<std::byte> pixels(480*272*4);
   for(unsigned y=0;y<272;++y)for(unsigned x=0;x<480;++x){auto i=(y*480+x)*4;pixels[i]=std::byte(x%251);pixels[i+1]=std::byte(y%251);pixels[i+2]=std::byte((x^y)&255);pixels[i+3]=std::byte(255);}
   display_window_present_rgba(pixels,480,272);
   // Actual SDL mouse events select all six resolutions. The guest frame and
   // source texture stay 480x272, and content never touches the toolbar.
   for(int i=0;i<int(ui::resolutions.size());++i) {
    click(170,12);check(menu_open,"selector click did not open menu");
    click(170,ui::toolbar_height+i*ui::row_height+10);check(!menu_open&&choice==i,"selection did not apply");
    int w=0,h=0;SDL_GetWindowSize(window,&w,&h);check(w==ui::resolutions[i].width && h==ui::resolutions[i].height+40,"selected dimensions wrong");
    check(tw==480&&th==272,"output resizing changed source texture");
    render(false);int ow=0,oh=0;SDL_GetRendererOutputSize(renderer,&ow,&oh);check(ow==w&&oh==h,"dummy output size disagrees");
    std::vector<std::uint8_t> captured(std::size_t(w)*h*4);checked(SDL_RenderReadPixels(renderer,nullptr,SDL_PIXELFORMAT_RGBA32,captured.data(),w*4),"test readback");
    auto region=ui::fit(w,h,480,272);
    auto rgb=[&](int xx,int yy){auto j=(std::size_t(yy)*w+xx)*4;return std::array<unsigned,3>{captured[j],captured[j+1],captured[j+2]};};
    check(rgb(2,2)==std::array<unsigned,3>{27,32,42},"toolbar color missing");
    check(rgb(region.x,region.y)==std::array<unsigned,3>{0,0,0},"source origin moved/corrupted");
    if(i<4){const unsigned factor=i+1;
     // Exhaustive 1x/2x/3x/4x nearest source-copy check (one sample per source
     // pixel plus all repeated pixels); counts are actual comparisons.
     for(unsigned y=0;y<unsigned(region.h);++y)for(unsigned x=0;x<unsigned(region.w);++x){
      const unsigned sx=x/factor,sy=y/factor;check(rgb(region.x+x,region.y+y)==std::array<unsigned,3>{sx%251,sy%251,(sx^sy)&255},"nearest resize altered framebuffer pixel");
     }
    }
   }
   focus(true);key(SDL_SCANCODE_W);check(sample().analog_y==0,"movement key not delivered");
   click(170,12);check(menu_open && sample().analog_y==128,"UI did not neutralize movement");
   key(SDL_SCANCODE_DOWN);key(SDL_SCANCODE_RETURN);check(!menu_open,"keyboard selection failed");check(sample().buttons==0&&sample().analog_y==128,"UI navigation leaked into PSP controls");
   key(SDL_SCANCODE_R,true,KMOD_ALT);check(menu_open,"Alt-R menu shortcut");key(SDL_SCANCODE_ESCAPE);check(!menu_open&&!closed,"Escape closed app instead of menu");
   key(SDL_SCANCODE_R);check((sample().buttons&0x200)!=0,"ordinary R PSP input");focus(false);check(sample().buttons==0&&sample().analog_y==128,"focus loss left stale input");
   focus(true);check(sample().buttons==0,"focus regain synthesized input");
   SDL_SetWindowSize(window,1011,691);poll();render();check(tw==480&&th==272,"manual resize changed texture");
   rejected=false;try{display_window_present_rgba(pixels,0,272);}catch(const psprecomp::Error&){rejected=true;}check(rejected,"zero frame not rejected");
   rejected=false;try{display_window_present_rgba(std::span<const std::byte>(pixels.data(),3),480,272);}catch(const psprecomp::Error&){rejected=true;}check(rejected,"short frame not rejected");
   // Actual rendered host-system modal; it is a presentation layer, never a
   // modification of source framebuffer/guest memory. Verify draw and removal.
   auto snapshot=[&]{render(false);int w=0,h=0;SDL_GetRendererOutputSize(renderer,&w,&h);std::vector<unsigned char> out(std::size_t(w)*h*4);checked(SDL_RenderReadPixels(renderer,nullptr,SDL_PIXELFORMAT_RGBA32,out.data(),w*4),"modal readback");return out;};
  const auto before=snapshot();MessageDialogView modal;modal.visible=true;modal.cancel=true;modal.ok=true;modal.text="Data cannot be loaded.\nSystem message requires input.";
   key(SDL_SCANCODE_F9);check(inspect_textures,"F9 did not enable texture panel");check(snapshot()!=before,"texture panel did not render");
   key(SDL_SCANCODE_F9,false);key(SDL_SCANCODE_F9);check(!inspect_textures,"F9 did not dismiss texture panel");check(snapshot()==before,"texture panel dismissal did not restore pixels");key(SDL_SCANCODE_F9,false);
   display_window_set_message_dialog(modal);const auto shown=snapshot();std::size_t changes=0;for(std::size_t i=0;i<shown.size();++i)changes+=shown[i]!=before[i];
   check(changes>10000,"system modal did not draw");check(tw==480&&th==272,"modal changed source texture geometry");
   display_window_set_message_dialog({});check(snapshot()==before,"dismissed modal did not restore exact presentation");
   modal.visible=true;modal.text=std::string(512,'\n');modal.scroll=512;display_window_set_message_dialog(modal);render(false);display_window_set_message_dialog({});
   check(wrap_message("abc def ghi",7)==std::vector<std::string>{"ABC DEF"," GHI"},"bounded text wrap changed");
   SDL_Event quit{};quit.type=SDL_QUIT;event(quit);check(display_window_close_requested(),"close event ignored");
   display_window_shutdown();check(!window&&!texture&&!renderer&&!pad,"shutdown leaked handles");
  }
  error.clear();std::cerr<<"PASS "<<checks<<" display/resolution/input/pixel checks\n";return true;
 }catch(const std::exception& e){display_window_shutdown();error="after "+std::to_string(checks)+" checks: "+e.what();return false;}
}
} // namespace vcs

namespace renegade::input008 {
RawPad live_keyboard_mouse() {
 using namespace vcs;
 poll();load_bindings();RawPad r;
 r.connected=true;
 r.enabled=window&&focused&&!menu_open&&!closed&&!message_view.visible&&!text_entry.active;
 if(!r.enabled){mouse_dx=mouse_dy=0;wheel_up=wheel_down=0;mouse_moved=false;return r;}
 r.lx=keys[SDL_SCANCODE_A]==keys[SDL_SCANCODE_D]?0:keys[SDL_SCANCODE_A]?-32767:32767;
 r.ly=keys[SDL_SCANCODE_W]==keys[SDL_SCANCODE_S]?0:keys[SDL_SCANCODE_W]?-32767:32767;
 for(unsigned i=0;i<15;++i)if(binding_held(bindings[i]))r.buttons|=1u<<i;
 r.lt=binding_held(bindings[15])?32767:0; r.rt=binding_held(bindings[16])?32767:0;
 r.mouse_look=true; r.mouse_dx=float(mouse_dx); r.mouse_dy=float(mouse_dy);
 r.activity=mouse_moved||r.lx||r.ly||r.buttons||r.lt||r.rt||mouse_buttons[1]||mouse_buttons[2]||wheel_up||wheel_down;
 mouse_dx=mouse_dy=0;mouse_moved=false; wheel_up=wheel_down=0; // wheel steps count for one sample
 return r;
}
RawPad live_gamepad() {
 vcs::poll();RawPad r;
 if(!vcs::pad || !SDL_GameControllerGetAttached(vcs::pad))return r;
 r.connected=true;
 r.enabled=vcs::window&&vcs::focused&&!vcs::menu_open&&!vcs::closed&&!vcs::message_view.visible;
 if(!r.enabled)return r;
 r.lx=SDL_GameControllerGetAxis(vcs::pad,SDL_CONTROLLER_AXIS_LEFTX);
 r.ly=SDL_GameControllerGetAxis(vcs::pad,SDL_CONTROLLER_AXIS_LEFTY);
 r.rx=SDL_GameControllerGetAxis(vcs::pad,SDL_CONTROLLER_AXIS_RIGHTX);
 r.ry=SDL_GameControllerGetAxis(vcs::pad,SDL_CONTROLLER_AXIS_RIGHTY);
 r.lt=SDL_GameControllerGetAxis(vcs::pad,SDL_CONTROLLER_AXIS_TRIGGERLEFT);
 r.rt=SDL_GameControllerGetAxis(vcs::pad,SDL_CONTROLLER_AXIS_TRIGGERRIGHT);
 for(unsigned i=0;i<=14;++i)
  if(SDL_GameControllerGetButton(vcs::pad,static_cast<SDL_GameControllerButton>(i)))r.buttons|=1u<<i;
 return r;
}
}
