#include "control_context009.hpp"
#include "material_audit009.hpp"
#include "modern_input008.hpp"
#include "psprecomp/elf32.hpp"
#include "psprecomp/sha256.hpp"
#include "psprecomp/runtime.hpp"
#include "vcs_profile.hpp"
#include "vcs_config.hpp"
#include "display_window.hpp"
#include "audio_output.hpp"
#include "ge_gpu_backend.hpp"
#include "ge_renderer.hpp"
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <string>
namespace psprecomp { void register_generated_functions(Runtime&); void register_supplemental_functions(Runtime&); }
namespace renegade { void install_extra_hle(psprecomp::Runtime&); void install_platform_services(psprecomp::Runtime&); void install_psmf_services(psprecomp::Runtime&); }
namespace renegade { void install_control_bridge008(psprecomp::Runtime&); }
namespace psprecomp {void recomp_unit_0073(Runtime&,AllegrexContext&);}
int main(int argc,char** argv) {
    if(argc<3 || argc>4) { std::cerr<<"Usage: RenegadeNative BOOT.BIN extracted-disc-root [max-dispatches]\n"; return 2; }
    auto runtime=std::make_unique<psprecomp::Runtime>();auto& rt=*runtime;
    try {
        std::string error;
        constexpr const char* expected_boot = "f4c7a9ef93475fc8017f649346ef79b599649dc47462ec419e9fd373146f8c68";
        if(!std::filesystem::is_regular_file(argv[1]) || std::filesystem::file_size(argv[1])!=4403020u ||
           psprecomp::sha256_file(argv[1])!=expected_boot)
            throw std::runtime_error("BOOT.BIN identity mismatch: this native build requires the original ULUS10292 executable (SHA-256 f4c7a9ef...146f8c68)");
        const std::filesystem::path disc=argv[2];
        if(!std::filesystem::is_directory(disc/"PSP_GAME/USRDIR") ||
           !std::filesystem::is_regular_file(disc/"PSP_GAME/PARAM.SFO") ||
           psprecomp::sha256_file(disc/"PSP_GAME/PARAM.SFO")!="18c944abd8f28b44c95719d27211d0ec6dcb00a535c0ca1c60ff03658d584fd4")
            throw std::runtime_error("Disc-root identity mismatch: expected extracted ULUS10292 PSP_GAME directory");
        std::uint64_t budget=10000000ull;
        if(argc==4) {
            const std::string value=argv[3]; std::size_t used=0;
            if(value.empty() || value[0]=='-')throw std::runtime_error("Dispatch budget must be a positive integer");
            budget=std::stoull(value,&used);
            if(used!=value.size() || !budget)throw std::runtime_error("Dispatch budget must be a positive integer");
        }
        rt.set_game_root(argv[2]);
        vcs::initialize_vcs_configuration(std::filesystem::absolute(argv[0]).parent_path());
        auto elf=psprecomp::Elf32Image::from_file(argv[1]);
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
        std::cerr<<"[renegade] ERROR: "<<error.what()<<"\n";
        rt.report_hle_histogram(300);return 3;
    }
}
