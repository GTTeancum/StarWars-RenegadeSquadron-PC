#include "control_context009.hpp"
#include "material_audit009.hpp"
#include "modern_input008.hpp"
#include "pc_settings.hpp"
#include "psprecomp/elf32.hpp"
#include "psprecomp/sha256.hpp"
#include "psprecomp/runtime.hpp"
#include "vcs_profile.hpp"
#include "vcs_config.hpp"
#include "display_window.hpp"
#include "audio_output.hpp"
#include "ge_gpu_backend.hpp"
#include "ge_renderer.hpp"
#include <cctype>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <string>
#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif
namespace psprecomp { void register_generated_functions(Runtime&); void register_supplemental_functions(Runtime&); }
namespace renegade { void install_extra_hle(psprecomp::Runtime&); void install_platform_services(psprecomp::Runtime&); void install_psmf_services(psprecomp::Runtime&); }
namespace renegade { void install_control_bridge008(psprecomp::Runtime&); }
namespace psprecomp {void recomp_unit_0073(Runtime&,AllegrexContext&);}
namespace {
// Installed layout, used when the game is started with no arguments (double-clicked):
//   <install>\RenegadeSquadron.exe, RenegadeSquadron.ini, runtime DLLs
//   <install>\data\PSP_GAME\...   extracted disc
//   <install>\mods\textures\...   optional replacement textures
//   <install>\SAVEDATA\...        created by the game
// The settings file supplies what Play-RenegadeSquadronPC.ps1 sets for PC mode. Environment
// variables that are already set win, so scripted runs keep working.
std::filesystem::path executable_directory(const char* argv0) {
#if defined(_WIN32)
    std::wstring buffer(32768u,L'\0');
    const DWORD length=GetModuleFileNameW(nullptr,buffer.data(),static_cast<DWORD>(buffer.size()));
    if(length && length<buffer.size()) { buffer.resize(length); return std::filesystem::path(buffer).parent_path(); }
#endif
    return std::filesystem::absolute(argv0).parent_path();
}
std::string trimmed(std::string value) {
    const auto first=value.find_first_not_of(" \t\r\n"); if(first==std::string::npos) return {};
    return value.substr(first,value.find_last_not_of(" \t\r\n")-first+1u);
}
std::string lower(std::string value) { for(char& c:value) c=static_cast<char>(std::tolower(static_cast<unsigned char>(c))); return value; }
void set_default(const char* name,const std::string& value) {
    if(std::getenv(name)) return;
#if defined(_WIN32)
    _putenv_s(name,value.c_str());
#else
    setenv(name,value.c_str(),1);
#endif
}
void apply_installed_settings(const std::filesystem::path& root) {
    const std::filesystem::path ini=root/"RenegadeSquadron.ini";
    std::map<std::string,std::string> settings;
    if(std::ifstream file{ini}) {
        std::string line,section;
        while(std::getline(file,line)) {
            if(line.size()>=3u && static_cast<unsigned char>(line[0])==0xEFu) line.erase(0,3);
            if(const auto comment=line.find_first_of(";#"); comment!=std::string::npos) line.resize(comment);
            line=trimmed(line); if(line.empty()) continue;
            if(line.front()=='[' && line.back()==']') { section=lower(trimmed(line.substr(1,line.size()-2))); continue; }
            const auto eq=line.find('='); if(eq==std::string::npos) continue;
            settings[section+"."+lower(trimmed(line.substr(0,eq)))]=trimmed(line.substr(eq+1));
        }
        set_default("PSPRECOMP_CONFIG",ini.string()); // [Display]/[Rendering]/[Audio] go to the shared configuration reader.
    }
    const auto get=[&](const char* key,const char* fallback) { const auto it=settings.find(key); return it==settings.end()||it->second.empty()?std::string(fallback):it->second; };
    const auto flag=[&](const char* key,bool fallback) { const std::string v=lower(get(key,fallback?"true":"false")); return v=="1"||v=="true"||v=="yes"||v=="on"; };
    // Window, audio and the PC-mode renderer: DirectX 12 on the graphics card, presented straight to the window.
    set_default("PSPRECOMP_WINDOW","1"); set_default("PSPRECOMP_AUDIO","1"); set_default("PSPRECOMP_FRAME_LIMIT","1");
    set_default("PSPRECOMP_RASTER_THREADS","1"); set_default("PSPRECOMP_GE_BACKEND","directx12");
    set_default("PSPRECOMP_DX12_GE_READBACK","0"); set_default("PSPRECOMP_DX12_GE_STRICT","1");
    set_default("PSPRECOMP_GE_GPU_SKIP_SOFTWARE_RASTER","1"); set_default("PSPRECOMP_GE_GPU_HW_TRANSFORM","1");
    set_default("PSPRECOMP_GE_GPU_HW_CULL","0");
    set_default("RENEGADE_HD_CAPTURE","0"); set_default("RENEGADE_HD_PRESENT","0"); set_default("RENEGADE_HD_START_VBLANK","0");
    set_default("RENEGADE_FXAA","0"); set_default("RENEGADE_HD_SURFACE_TEXTURES","0");
    // [Graphics]
    set_default("RENEGADE_OUTPUT_RESOLUTION",get("graphics.windowsize","1280x720"));
    set_default("RENEGADE_FULLSCREEN",flag("graphics.fullscreen",false)?"1":"0");
    set_default("RENEGADE_FRAME_RATE_CAP",get("graphics.frameratecap","60"));
    const bool per_pixel=flag("graphics.perpixellighting",true);
    set_default("RENEGADE_PER_PIXEL_LIGHTING",per_pixel?"1":"0");
    set_default("RENEGADE_SHADOWS",per_pixel && flag("graphics.shadows",true)?"1":"0");
    set_default("RENEGADE_BLOOM",flag("graphics.bloom",true)?"1":"0");
    set_default("RENEGADE_FOG_CURVE",flag("graphics.smoothfog",false)?"smooth":"linear");
    if(std::filesystem::is_directory(root/"mods"/"files") || (flag("graphics.replacementtextures",true) && std::filesystem::is_directory(root/"mods"/"textures")))
        set_default("RENEGADE_OVERRIDE_ROOT",(root/"mods").string());
    // [Controller]
    set_default("RENEGADE_CONTROLS",lower(get("controller.scheme","modern")));
    set_default("RENEGADE_LOOK_X",get("controller.looksensitivityx","0.5"));
    set_default("RENEGADE_LOOK_Y",get("controller.looksensitivityy","0.5"));
    set_default("RENEGADE_LOOK_CURVE",get("controller.lookcurve","1.0"));
    set_default("RENEGADE_LEFT_DEADZONE",get("controller.leftdeadzone","0.2394"));
    set_default("RENEGADE_RIGHT_DEADZONE",get("controller.rightdeadzone","0.2652"));
    set_default("RENEGADE_TRIGGER_THRESHOLD",get("controller.triggerthreshold","0.1176"));
    set_default("RENEGADE_INVERT_Y",flag("controller.inverty",false)?"1":"0");
    // [Mouse] and [Keyboard]: mouse look and the pad buttons the keys stand for.
    set_default("RENEGADE_MOUSE_SENSITIVITY",get("mouse.sensitivity","1.0"));
    set_default("RENEGADE_MOUSE_INVERT_Y",flag("mouse.inverty",false)?"1":"0");
    for(const char* button:{"A","B","X","Y","Back","Start","LS","RS","LB","RB","Up","Down","Left","Right","LT","RT","Pause"}) {
        const std::string key=std::string("keyboard.")+lower(button);
        if(const auto it=settings.find(key); it!=settings.end() && !it->second.empty()) set_default((std::string("RENEGADE_KEY_")+button).c_str(),it->second);
    }
    // SDL keeps Xbox-compatible/XInput pads enabled.
    for(const char* hint:{"SDL_XINPUT_ENABLED","SDL_JOYSTICK_RAWINPUT","SDL_JOYSTICK_RAWINPUT_CORRELATE_XINPUT",
                          "SDL_JOYSTICK_HIDAPI_XBOX","SDL_JOYSTICK_HIDAPI_XBOX_360","SDL_JOYSTICK_HIDAPI_XBOX_ONE"}) set_default(hint,"1");
}
void report_startup_error(bool installed,const std::string& message) {
#if defined(_WIN32)
    if(installed) {
        const std::string text="The game could not start.\n\n"+message+
            "\n\nThe game data must be the extracted US disc (ULUS10292), with its PSP_GAME folder placed in the \"data\" folder next to RenegadeSquadron.exe.";
        MessageBoxA(nullptr,text.c_str(),"Star Wars Battlefront: Renegade Squadron",MB_OK|MB_ICONERROR);
    }
#else
    (void)installed;(void)message;
#endif
}
}
int main(int argc,char** argv) {
    const bool installed=argc==1;
    std::filesystem::path boot_path,disc_path;
    if(installed) {
        const auto root=executable_directory(argv[0]);
        std::error_code ignored; std::filesystem::current_path(root,ignored);
#if defined(_WIN32)
        // Started without a console (double-clicked): keep the log beside the game for troubleshooting.
        const HANDLE err=GetStdHandle(STD_ERROR_HANDLE);
        if(err==nullptr || err==INVALID_HANDLE_VALUE) { FILE* log=nullptr; _wfreopen_s(&log,(root/"RenegadeSquadron.log").wstring().c_str(),L"w",stderr); }
#endif
        apply_installed_settings(root);
        renegade::pc_settings::set_settings_file(root/"RenegadeSquadron.ini");
        disc_path=root/"data"; boot_path=disc_path/"PSP_GAME"/"SYSDIR"/"BOOT.BIN";
    } else if(argc<3 || argc>4) { std::cerr<<"Usage: RenegadeNative BOOT.BIN extracted-disc-root [max-dispatches]\n       RenegadeNative   (installed layout: data\\PSP_GAME beside the executable)\n"; return 2; }
    else { boot_path=argv[1]; disc_path=argv[2]; }
    auto runtime=std::make_unique<psprecomp::Runtime>();auto& rt=*runtime;
    try {
        std::string error;
        constexpr const char* expected_boot = "f4c7a9ef93475fc8017f649346ef79b599649dc47462ec419e9fd373146f8c68";
        if(!std::filesystem::is_regular_file(boot_path) || std::filesystem::file_size(boot_path)!=4403020u ||
           psprecomp::sha256_file(boot_path)!=expected_boot)
            throw std::runtime_error("BOOT.BIN identity mismatch: this native build requires the original ULUS10292 executable (SHA-256 f4c7a9ef...146f8c68)");
        const std::filesystem::path disc=disc_path;
        if(!std::filesystem::is_directory(disc/"PSP_GAME/USRDIR") ||
           !std::filesystem::is_regular_file(disc/"PSP_GAME/PARAM.SFO") ||
           psprecomp::sha256_file(disc/"PSP_GAME/PARAM.SFO")!="18c944abd8f28b44c95719d27211d0ec6dcb00a535c0ca1c60ff03658d584fd4")
            throw std::runtime_error("Disc-root identity mismatch: expected extracted ULUS10292 PSP_GAME directory");
        std::uint64_t budget=installed?1000000000000ull:10000000ull;
        if(argc==4) {
            const std::string value=argv[3]; std::size_t used=0;
            if(value.empty() || value[0]=='-')throw std::runtime_error("Dispatch budget must be a positive integer");
            budget=std::stoull(value,&used);
            if(used!=value.size() || !budget)throw std::runtime_error("Dispatch budget must be a positive integer");
        }
        rt.set_game_root(disc_path);
        vcs::display_window_set_fonts(disc_path/"PSP_GAME"/"USRDIR"/"GRAPHICS"/"FONTS.ASR");
        vcs::initialize_vcs_configuration(installed?executable_directory(argv[0]):std::filesystem::absolute(argv[0]).parent_path());
        auto elf=psprecomp::Elf32Image::from_file(boot_path);
        const auto relocations=elf.load_and_relocate(rt.memory());
        if(relocations.invalid || relocations.unsupported)
            throw std::runtime_error("Executable relocation was not fully supported");
        std::cerr<<"[renegade] verified ULUS10292 BOOT and SFO; relocations="<<relocations.total<<" invalid=0 unsupported=0\n";
        psprecomp::register_generated_functions(rt);
        psprecomp::register_supplemental_functions(rt);
        // ULUS10292 BOOT.BIN image ends below this aligned arena start.
        vcs::install_profile(rt,0x08C40000u);
        renegade::install_control_bridge008(rt);
        renegade::context009::install(rt,psprecomp::recomp_unit_0073);
        renegade::install_extra_hle(rt);
        renegade::install_platform_services(rt);
        renegade::install_psmf_services(rt);
        rt.cpu().gpr[28]=0; // Verified module GP for this exact BOOT.BIN.
        rt.cpu().gpr[31]=0;rt.cpu().gpr[4]=0;rt.cpu().gpr[5]=0;
        if(!vcs::initialize_ge_gpu_backend(error)) throw std::runtime_error(error);
        const auto initialized_gpu=vcs::ge_gpu_backend_report();
        std::cerr<<"[ge-backend] active="<<vcs::ge_gpu_backend_name(initialized_gpu.active)
                 <<" target="<<initialized_gpu.offscreen_width<<"x"<<initialized_gpu.offscreen_height
                 <<" msaa="<<initialized_gpu.dx12_msaa_samples
                 <<" message="<<initialized_gpu.message<<"\n";
        std::cerr<<"[renegade] ULUS10292 native AOT bring-up; no gameplay acceptance claimed\n";
        renegade::materials009::begin_from_environment(renegade::input008::frame_number);
        std::cerr<<"[renegade] entry=0x"<<std::hex<<elf.runtime_entry()<<std::dec<<"\n";
        vcs::install_display_heartbeat();
        vcs::install_starvation_preemption();
        vcs::display_window_start();
        rt.run(elf.runtime_entry(),budget);
        std::cerr<<"[renegade] STOP: "<<rt.stop_reason()<<" pc=0x"<<std::hex<<rt.cpu().pc<<std::dec<<" work="<<rt.dispatch_work_count()<<"\n";
        rt.report_hle_histogram(300);vcs::report_disc_read_stats();vcs::report_present_stats();
        const auto gpu=vcs::ge_gpu_backend_report();const auto replacements=vcs::ge_override_gpu_stats();
        std::cerr<<"[ge-backend-result] frames="<<gpu.game_frames<<" draws="<<gpu.game_draw_calls
                 <<" missing_textures="<<gpu.game_textured_draws_without_texture<<" uploads="<<gpu.decoded_texture_uploads
                 <<" replacement_draws="<<replacements.draws<<" replacement_uploads="<<replacements.uploads
                 <<" original_alpha_uploads="<<replacements.alpha_uploads
                 <<" largest_replacement="<<replacements.max_width<<"x"<<replacements.max_height<<"\n";
        if(const char* path=std::getenv("RENEGADE_RAM_SNAPSHOT")) {
            auto bytes=rt.memory().bytes();std::ofstream file(path,std::ios::binary);
            file.write(reinterpret_cast<const char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));
        }
        renegade::materials009::finish();
        vcs::audio_output_shutdown();vcs::display_window_shutdown();vcs::shutdown_ge_gpu_backend();
        const auto reason=rt.stop_reason();
        return reason.find("VBlank diagnostic stop")==0 || reason.find("Controller diagnostic stop")==0 || reason=="Display window closed by the user" ? 0 : 4;
    } catch(const std::exception& error) {
        std::cerr<<"[renegade] ERROR: "<<error.what()<<"\n";report_startup_error(installed,error.what());
        rt.report_hle_histogram(300);return 3;
    }
}
