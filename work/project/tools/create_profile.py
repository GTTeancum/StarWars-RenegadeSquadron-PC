#!/usr/bin/env python3
"""Create a Renegade bring-up profile from the supplied, pinned MIT framework."""
from pathlib import Path
import re, json, difflib
root=Path('/mnt/data/renegade');r=root/'intake/sources/PSPRecomp';v=r/'profiles/vcs/host';p=r/'profiles/renegade';h=p/'host';h.mkdir(parents=True,exist_ok=True)
s=(v/'vcs_profile.cpp').read_text();original=s
start=s.index('void install_profile(')
a=s.index('install_native_fast_paths(runtime);',start)
a=s.rfind('\n',0,a)+1
b=s.index('std::cerr << "[frame-rate] target="',a);b=s.rfind('\n',0,b)+1
s=s[:a]+'    // Renegade: never install Vice City Stories game-address replacements.\n'+s[b:]
a=s.index('runtime.register_function(0x08B562D8u',start);a=s.rfind('\n',0,a)+1
b=s.index('runtime.register_hle("SysMemUserForUser"',a);b=s.rfind('\n',0,b)+1
s=s[:a]+'    // Renegade: VCS sprintf/path hash/module loader/deflate replacements removed.\n'+s[b:]
s=s.replace('vcs_configuration().timing.frame_rate','30u')
s=re.sub(r'vcs_camera_set_axes\(host\.camera_x,\s*host\.camera_y\);','/* VCS camera injection disabled for Renegade. */',s)
s=re.sub(r'vcs_set_host_drive_inputs\(host\.accelerate,\s*host\.brake\);','/* VCS vehicle injection disabled for Renegade. */',s)
s=s.replace('VCS module_start stack','Renegade module_start stack')
(h/'psp_services.cpp').write_text('// Renegade bring-up fork of upstream MIT-licensed PSP services.\n// No Vice City Stories native game-address replacements are installed.\n'+s)
(root/'patches/renegade-services.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='upstream/profiles/vcs/host/vcs_profile.cpp',tofile='profiles/renegade/host/psp_services.cpp')))
registry={}
for path in (root/'intake/reference/pspsdk/src').rglob('*.S'):
 for lib,nid,name in re.findall(r'IMPORT_FUNC\s+"([^"]+)",\s*0x([0-9A-Fa-f]+),\s*(\w+)',path.read_text(errors='replace')):
  registry[(lib,int(nid,16))]=name
extra=['#include "psprecomp/runtime.hpp"','namespace renegade {','void install_extra_hle(psprecomp::Runtime& rt) {']
for (lib,nid),name in sorted(registry.items()):extra.append(f'    rt.nids().add("{lib}", 0x{nid:08X}u, "{name}");')
extra+=['}','}'];(h/'extra_hle.cpp').write_text('\n'.join(extra)+'\n')
main=r'''#include "psprecomp/elf32.hpp"
#include "psprecomp/runtime.hpp"
#include "vcs_profile.hpp"
#include "vcs_config.hpp"
#include "display_window.hpp"
#include "audio_output.hpp"
#include "ge_gpu_backend.hpp"
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <string>
namespace psprecomp { void register_generated_functions(Runtime&); }
namespace renegade { void install_extra_hle(psprecomp::Runtime&); }
int main(int argc,char** argv) {
    if(argc<3 || argc>4) { std::cerr<<"Usage: RenegadeNative BOOT.BIN extracted-disc-root [max-dispatches]\n"; return 2; }
    auto runtime=std::make_unique<psprecomp::Runtime>();auto& rt=*runtime;
    try {
        rt.set_game_root(argv[2]);
        vcs::initialize_vcs_configuration(std::filesystem::absolute(argv[0]).parent_path());
        auto elf=psprecomp::Elf32Image::from_file(argv[1]);
        elf.load_and_relocate(rt.memory());
        psprecomp::register_generated_functions(rt);
        // ULUS10292 BOOT.BIN image ends below this aligned arena start.
        vcs::install_profile(rt,0x08C40000u);
        renegade::install_extra_hle(rt);
        if(auto module=elf.find_module_info(rt.memory())) rt.cpu().gpr[28]=module->gp;
        rt.cpu().gpr[31]=0;rt.cpu().gpr[4]=0;rt.cpu().gpr[5]=0;
        std::string error;
        if(!vcs::initialize_ge_gpu_backend(error)) throw std::runtime_error(error);
        std::cerr<<"[renegade] ULUS10292 native AOT bring-up; no gameplay acceptance claimed\n";
        std::cerr<<"[renegade] entry=0x"<<std::hex<<elf.runtime_entry()<<std::dec<<" functions="<<rt.function_count()<<"\n";
        vcs::install_display_heartbeat();
        vcs::install_starvation_preemption();
        vcs::display_window_start();
        rt.run(elf.runtime_entry(),argc==4?std::stoull(argv[3]):10000000ull);
        std::cerr<<"[renegade] STOP: "<<rt.stop_reason()<<" pc=0x"<<std::hex<<rt.cpu().pc<<std::dec<<" work="<<rt.dispatch_work_count()<<"\n";
        rt.report_hle_histogram(300);vcs::report_disc_read_stats();vcs::report_present_stats();
        if(const char* path=std::getenv("RENEGADE_RAM_SNAPSHOT")) {
            auto bytes=rt.memory().bytes();std::ofstream file(path,std::ios::binary);
            file.write(reinterpret_cast<const char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));
        }
        vcs::audio_output_shutdown();vcs::display_window_shutdown();vcs::shutdown_ge_gpu_backend();
        return 0;
    } catch(const std::exception& error) {
        std::cerr<<"[renegade] ERROR: "<<error.what()<<"\n";
        rt.report_hle_histogram(300);return 3;
    }
}
'''
(h/'main.cpp').write_text(main)
cm=r'''set(VENDOR_HOST "${CMAKE_CURRENT_SOURCE_DIR}/../vcs/host")
file(GLOB RENEGADE_GENERATED CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/generated/generated_*.cpp")
if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/generated/generated_registry.cpp")
  message(FATAL_ERROR "Generate Renegade's AOT sources before configuring this profile")
endif()
add_library(renegade_aot STATIC ${RENEGADE_GENERATED})
target_link_libraries(renegade_aot PUBLIC psprecomp_core)
target_include_directories(renegade_aot PRIVATE generated)
target_compile_options(renegade_aot PRIVATE -O0 -g0 -w)
target_precompile_headers(renegade_aot PRIVATE <psprecomp/runtime.hpp> <bit> <cmath> <cstdint> <limits>)
set(SERVICES host/psp_services.cpp host/extra_hle.cpp)
foreach(name framebuffer_capture display_window audio_output vcs_config vcs_camera_input
  vcs_vehicle_input vcs_fps_overlay vcs_media_decoder vcs_project2dfx
  vcs_project2dfx_lights vcs_draw_distance_patch vcs_runtime_log
  vcs_hdr_post_dx12_stub ge_renderer ge_gpu_backend_dx12 dx12_presenter)
  list(APPEND SERVICES "${VENDOR_HOST}/${name}.cpp")
endforeach()
add_library(renegade_services STATIC ${SERVICES})
set(RENEGADE_SDK "/mnt/data/renegade/intake/sdk" CACHE PATH "Private scratch SDK overlay")
target_include_directories(renegade_services PUBLIC "${VENDOR_HOST}"
  "${RENEGADE_SDK}/usr/include/x86_64-linux-gnu" "${RENEGADE_SDK}/usr/include")
target_link_libraries(renegade_services PUBLIC psprecomp_core ${CMAKE_DL_LIBS})
target_compile_options(renegade_services PRIVATE -O2 -g0)
foreach(pair "avcodec;61" "avformat;61" "avutil;59" "swresample;5" "swscale;8")
  list(GET pair 0 name)
  list(GET pair 1 abi)
  find_library(RENEGADE_${name} NAMES ${name} lib${name}.so.${abi} REQUIRED)
  target_link_libraries(renegade_services PUBLIC ${RENEGADE_${name}})
endforeach()
add_executable(RenegadeNative host/main.cpp)
target_link_libraries(RenegadeNative PRIVATE renegade_aot renegade_services)
set_target_properties(RenegadeNative PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
'''
(p/'CMakeLists.txt').write_text(cm)
print('Profile created;',len(registry),'SDK import names; VCS game-address patches not installed.')
