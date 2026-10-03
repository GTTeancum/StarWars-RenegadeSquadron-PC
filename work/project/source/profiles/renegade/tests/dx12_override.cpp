#include "../host/override_store.hpp"
#include "../host/test_environment010.hpp"
#include "../host/diagnostic_gpu_capture.hpp"
#include "../host/movie_gpu_present.hpp"
#include "ge_renderer.hpp"
#include "ge_gpu_backend.hpp"
#include "vcs_config.hpp"
#include <bit>
#include <chrono>
#include <fstream>
#include <iostream>
#include <algorithm>
using namespace renegade::overrides;
int main(){
    const auto dir=std::filesystem::temp_directory_path()/("renegade-dx12-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    try{
        auto check=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
        std::filesystem::create_directories(dir/"textures");
        {std::ofstream f(dir/"gpu.ini");f<<"[Rendering]\nBackend=DirectX12\nDX12GEColor=true\nInternalResolutionMode=Custom\nInternalWidth=1280\nInternalHeight=720\nMSAA=1\nDepthPrecision=16\n";}
        using renegade::test010::set_environment;
        set_environment("PSPRECOMP_CONFIG",(dir/"gpu.ini").string().c_str());
        set_environment("PSPRECOMP_DX12_GE_READBACK","1");set_environment("PSPRECOMP_DX12_GE_STRICT","1");
        set_environment("PSPRECOMP_GE_GPU_SKIP_SOFTWARE_RASTER","0");set_environment("PSPRECOMP_GE_GPU_HW_TRANSFORM","0");
        set_environment("RENEGADE_OVERRIDE_ROOT",dir.string().c_str());set_environment("RENEGADE_DUMP_TEXTURES",(dir/"dump").string().c_str());
        std::vector<unsigned char> tga(18);tga[2]=2;tga[12]=3;tga[14]=1;tga[16]=32;tga[17]=0x28;
        tga.insert(tga.end(),{0,255,0,255,255,0,0,255,255,255,255,255});
        auto stage=[&](const std::vector<std::uint8_t>& original,bool source_alpha){
            const auto id=texture_id(1,1,original);std::ofstream f(dir/"textures"/(id+".tga"),std::ios::binary);
            f.write(reinterpret_cast<const char*>(tga.data()),tga.size());f.close();
            if(source_alpha){std::ofstream policy(dir/"textures"/(id+".json"));policy<<"{\"alpha\":\"original\"}";}
        };
        stage({255,0,0,255},false);stage({200,20,10,64},true);
        vcs::initialize_vcs_configuration(dir);std::string error;
        check(vcs::initialize_ge_gpu_backend(error),error.c_str());
        check(vcs::ge_gpu_backend_graphics_ready(),"DX12 graphics path unavailable");
        psprecomp::GuestMemory memory;vcs::GeTransformState transform{};vcs::reset_ge_transform_state(transform);
        constexpr unsigned vertices=0x08801000,source=0x08810000,fb=0x04000000;
        std::array<unsigned,256> c{};c[0x9d]=512;c[0xd2]=3;c[0xd5]=479|(271<<10);
        c[0x12]=0x800000|3|(7<<2)|(3<<7);c[0x1e]=1;c[0xa0]=source&0xffffff;c[0xa8]=0x080001;c[0xc3]=3;c[0xc9]=3;c[0xde]=1;
        for(unsigned n=0;n<2;++n){const auto p=vertices+n*24;
            for(unsigned at:{0,4,12,16})memory.aot_store32(p+at,std::bit_cast<unsigned>(float(n)));
            memory.aot_store32(p+8,0xffffffff);memory.aot_store32(p+20,0);
        }
        memory.aot_store32(source,0xff0000ff);vcs::GeRenderStats stats{};
        vcs::ge_gpu_backend_set_display_framebuffer(fb);
        auto draw=[&](){check(vcs::render_ge_primitive(memory,c,transform,vertices,0,(6<<16)|2,stats,error),error.c_str());};
        draw();check(vcs::ge_gpu_backend_finish_color_frame(1),"DX12 did not render a real frame");
        const auto report=vcs::ge_gpu_backend_report();const auto pixels=vcs::ge_gpu_backend_game_frame_rgba();
        check(report.offscreen_width==1280&&report.offscreen_height==720&&pixels.size()==1280*720*4,"GPU target must be true 720p");
        auto at=[&](unsigned i){return std::to_integer<unsigned>(pixels[i]);};
        check(at(0)==0&&at(1)==255&&at(2)==0,"GPU replacement first subpixel green");
        check(at(4)==0&&at(5)==0&&at(6)==255,"GPU replacement second subpixel blue");
        check(at(8)==255&&at(9)==255&&at(10)==255,"GPU replacement third subpixel white");
        const auto filtered=vcs::ge_fxaa_gpu_rgba(fb,1280,720,pixels);
        check(std::equal(pixels.begin(),pixels.begin()+12,filtered.begin()),"GPU presentation FXAA retains HUD detail");
        const auto capture=renegade::diagnostic104::capture_gpu_frame(dir,"controller-current",1,fb,report,pixels,true);
        check(capture.captured&&capture.source_vblank==1&&capture.width==1280&&capture.height==720,"Controller capture must describe the current real GPU frame");
        auto verify_capture=[&](const std::string& name,std::span<const std::byte> expected){
            std::ifstream input(dir/name,std::ios::binary);std::string magic;unsigned width{},height{},maximum{};char separator{};
            input>>magic>>width>>height>>maximum;input.get(separator);
            check(magic=="P6"&&width==1280&&height==720&&maximum==255&&separator=='\n',"Controller HD PPM header");
            const std::vector<char> rgb((std::istreambuf_iterator<char>(input)),{});
            check(rgb.size()==1280*720*3,"Controller capture must not resample or truncate HD output");
            for(std::size_t n=0;n<1280*720;++n)for(unsigned channel=0;channel<3;++channel)
                check(static_cast<unsigned char>(rgb[n*3+channel])==std::to_integer<unsigned>(expected[n*4+channel]),"Controller capture pixels must equal GPU readback exactly");
        };
        verify_capture(capture.frame,pixels);verify_capture(capture.fxaa_frame,filtered);
        const auto stale=renegade::diagnostic104::capture_gpu_frame(dir,"controller-stale",2,fb,report,pixels,true);
        check(!stale.captured&&stale.source_vblank==1&&!std::filesystem::exists(dir/"controller-stale-gpu.ppm"),"A held old GPU frame must not be relabeled as a current pause");
        const auto unavailable=renegade::diagnostic104::capture_gpu_frame(dir,"controller-missing",1,fb,report,{},true);
        check(!unavailable.captured&&!std::filesystem::exists(dir/"controller-missing-gpu.ppm"),"No readback must retain native-only diagnostic status");
        bool incomplete_capture=false;try{renegade::diagnostic104::capture_gpu_frame(dir,"controller-truncated",1,fb,report,pixels.first(4),true);}catch(const std::exception&){incomplete_capture=true;}
        check(incomplete_capture&&!std::filesystem::exists(dir/"controller-truncated-gpu.ppm"),"Malformed readback must not publish a misleading HD capture");
        std::cout<<"Controller HD capture: current1280x720 pixels/FXAA exact; stale/missing rejected; truncated rejected\n";
        bool malformed=false;try{vcs::ge_fxaa_gpu_rgba(fb,1280,720,{});}catch(const std::exception&){malformed=true;}
        check(malformed,"GPU FXAA rejects incomplete readback");
        check(memory.aot_load32(source)==0xff0000ff,"GPU cannot modify authored guest texture");
        memory.aot_store32(source,0xff00ffff);draw();check(vcs::ge_gpu_backend_finish_color_frame(2),"GPU changed-source frame");
        const auto changed=vcs::ge_gpu_backend_game_frame_rgba();
        check(std::to_integer<unsigned>(changed[0])==255&&std::to_integer<unsigned>(changed[1])==255&&std::to_integer<unsigned>(changed[2])==0,"GPU cache must invalidate replacement on changed source");
        memory.aot_store32(source,0x400a14c8);draw();
        std::vector<std::byte> upload(12);check(vcs::ge_gpu_backend_copy_last_texture_rgba(upload),"GPU authored image upload missing");
        for(unsigned x=0;x<3;++x)check(std::to_integer<unsigned>(upload[x*4+3])==64,"GPU upload preserves original-alpha policy at replacement resolution");
        check(vcs::ge_override_gpu_stats().uploads==2&&vcs::ge_override_gpu_stats().alpha_uploads==1,"GPU replacement upload counters");
        check(std::filesystem::is_regular_file(dir/"dump"/(texture_id(1,1,std::vector<std::uint8_t>{255,0,0,255})+".tga")),"GPU lookup must dump original source");

        // A supplied replacement must also win when its original lives in a
        // registered VRAM framebuffer, rather than sampling live feedback.
        memory.aot_store32(fb,0xff0000ff);c[0xa0]=0;c[0xa8]=0x040001;
        draw();check(vcs::ge_gpu_backend_finish_color_frame(3),"GPU VRAM replacement frame");
        const auto replaced_vram=vcs::ge_gpu_backend_game_frame_rgba();
        check(std::to_integer<unsigned>(replaced_vram[0])==0&&std::to_integer<unsigned>(replaced_vram[1])==255,
              "Authored VRAM replacement must take priority over live framebuffer feedback");

        // Exercise the prepared world-geometry path, including a depth-only
        // clear and overlapping perspective vertices. Through-mode UI does
        // not reveal a disabled depth-write unit.
        vcs::GeGpuDrawDescriptor world{};
        world.framebuffer_address=fb;world.framebuffer_stride=512;world.framebuffer_format=3;
        world.depth_write_enabled=true;world.color_write_mask=0xffffffff;
        vcs::ge_gpu_backend_record_draw(world);
        std::array<vcs::GeGpuVertex,6> clear{{
            {0,0,65535,1,0},{480,0,65535,1,0},{480,272,65535,1,0},
            {0,0,65535,1,0},{480,272,65535,1,0},{0,272,65535,1,0}}};
        vcs::ge_gpu_backend_accumulate_color_triangles(world,clear);
        world.color_write_mask=0;world.depth_test_enabled=true;world.depth_function=4;
        auto triangle=[&](float z,float w,unsigned color){
            std::array<vcs::GeGpuVertex,3> v{{{10,10,z,w,color},{150,10,z,w,color},{10,150,z,w,color}}};
            vcs::ge_gpu_backend_record_draw(world);vcs::ge_gpu_backend_accumulate_color_triangles(world,v);
        };
        triangle(30000,2,0xff0000ff);triangle(15000,3,0xff00ff00);triangle(45000,4,0xffff0000);
        check(vcs::ge_gpu_backend_finish_color_frame(4),"GPU projected depth frame");
        const auto depth_pixels=vcs::ge_gpu_backend_game_frame_rgba();
        const unsigned center=(106*1280+106)*4;
        check(std::to_integer<unsigned>(depth_pixels[center])==0&&std::to_integer<unsigned>(depth_pixels[center+1])==255&&std::to_integer<unsigned>(depth_pixels[center+2])==0,
              "Projected world triangles must survive depth-only clear and retain nearest depth");
        world.texture_enabled=true;world.texture_width=1;world.texture_height=1;world.texture_format=3;
        world.texture_address=0x08800000;
        check(!vcs::ge_gpu_backend_is_framebuffer_feedback_texture(world),"RAM texture cannot alias framebuffer zero");
        check(vcs::ge_gpu_backend_texture_signature_needed(world),"RAM texture requires its own content signature");
        check(vcs::ge_gpu_backend_texture_needed(world),"RAM texture requires its own upload");
        check(!vcs::ge_gpu_backend_texture_available(world),"RAM texture cannot borrow a framebuffer image");
        world.texture_address=0x48800000;
        check(!vcs::ge_gpu_backend_is_framebuffer_feedback_texture(world),"Uncached RAM texture cannot alias framebuffer zero");
        world.texture_address=0x44000000;
        check(vcs::ge_gpu_backend_is_framebuffer_feedback_texture(world),"Uncached VRAM framebuffer feedback remains supported");

        // A triangle-shaped stencil mask clips a larger UI rectangle. Verify
        // fail and depth-fail operations as well as the ordinary pass path.
        world.texture_enabled=false;world.depth_test_enabled=false;world.depth_write_enabled=false;
        world.clear_mode=true;world.clear_alpha=true;world.color_write_mask=0x00ffffff;
        vcs::ge_gpu_backend_accumulate_color_triangles(world,clear); // clear alpha/stencil to zero
        world.clear_mode=false;world.clear_alpha=false;world.stencil={true,1,1,255,0,0,2};
        auto mask_triangle=[&](float x,float y,float z){
            std::array<vcs::GeGpuVertex,3> v{{{x,y,z,1,0},{x+100,y,z,1,0},{x,y+100,z,1,0}}};
            vcs::ge_gpu_backend_accumulate_color_triangles(world,v);
        };
        mask_triangle(200,50,0);
        world.stencil={true,0,2,255,2,0,0};mask_triangle(350,50,0); // NEVER, fail=REPLACE
        world.depth_test_enabled=true;world.depth_function=4;world.stencil={true,1,3,255,0,2,0};
        mask_triangle(10,10,45000); // fail existing nearer world depth, zfail=REPLACE
        world.depth_test_enabled=false;world.color_write_mask=0;world.stencil={true,2,1,255,0,0,0};
        auto fill=[&](unsigned color){
            auto full=clear;for(auto& v:full){v.z=0;v.rgba=color;}
            vcs::ge_gpu_backend_accumulate_color_triangles(world,full);
        };
        fill(0xff00ffff);
        world.stencil.reference=2;fill(0xffff0000); // reference-only change must not merge
        world.stencil.reference=3;fill(0xffffffff);
        check(vcs::ge_gpu_backend_finish_color_frame(5),"GPU stencil mask frame");
        const auto masked=vcs::ge_gpu_backend_game_frame_rgba();
        auto rgb=[&](unsigned x,unsigned y){const auto p=(y*1280+x)*4;return
            std::to_integer<unsigned>(masked[p])|(std::to_integer<unsigned>(masked[p+1])<<8)|(std::to_integer<unsigned>(masked[p+2])<<16);};
        check(rgb(600,200)==0x00ffff,"Stencil pass operation must mask UI to triangle interior");
        check(rgb(850,200)==0,"Stencil must reject UI outside its mask");
        check(rgb(1000,200)==0xff0000,"Stencil fail operation must update its mask");
        check(rgb(106,106)==0xffffff,"Stencil depth-fail operation must update its mask");

        // Fog boundaries may cross a single triangle. Clamping coefficients at
        // its vertices incorrectly turns a black-to-white boundary into a
        // triangle-wide gray ramp. Exercise actual GE float-vertex decode and
        // GPU shading, not an arithmetic duplicate of the implementation.
        c={};c[0x9d]=512;c[0xd2]=3;c[0xd5]=479|(271<<10);
        c[0x12]=(7<<2)|(3<<7);c[0x1f]=1;
        auto float24=[](float value){return std::bit_cast<unsigned>(value)>>8;};
        c[0x42]=float24(240);c[0x43]=float24(136);
        c[0x45]=float24(240);c[0x46]=float24(136);c[0xce]=float24(1);
        vcs::reset_ge_transform_state(transform);transform.projection[10]=0;
        const std::array<std::array<float,3>,3> fog_positions{{{-1,-1,-2},{1,-1,2},{-1,1,-2}}};
        for(unsigned n=0;n<3;++n){const auto p=vertices+n*16;
            memory.aot_store32(p,0xffffffff);
            for(unsigned k=0;k<3;++k)memory.aot_store32(p+4+k*4,std::bit_cast<unsigned>(fog_positions[n][k]));
        }
        check(vcs::render_ge_primitive(memory,c,transform,vertices,0,(3<<16)|3,stats,error),error.c_str());
        check(vcs::ge_gpu_backend_finish_color_frame(6),"GPU fog boundary frame");
        const auto fogged=vcs::ge_gpu_backend_game_frame_rgba();
        auto fog_red=[&](unsigned x){return std::to_integer<unsigned>(fogged[(50*1280+x)*4]);};
        check(fog_red(512)<=2,"Fog must stay fully black before its boundary");
        check(fog_red(704)>=48&&fog_red(704)<=55,"Fog transition must interpolate raw coefficients before clamping");
        check(fog_red(832)>=150&&fog_red(832)<=157,"Fog transition must retain its correct gradient");
        check(fog_red(1088)>=253,"Fog must become fully white after its boundary");
        // The same boundary must survive both model-space shader variants.
        vcs::GeGpuDrawDescriptor fog_draw{};
        fog_draw.framebuffer_address=fb;fog_draw.framebuffer_stride=512;fog_draw.framebuffer_format=3;
        fog_draw.fog_enabled=true;
        vcs::GeGpuHardwareTransform fog_transform{};
        fog_transform.model_to_clip[0]=fog_transform.model_to_clip[5]=fog_transform.model_to_clip[15]=1;
        fog_transform.model_to_view_z={0,0,1,0};fog_transform.fog_slope=1;
        fog_transform.viewport_scale_x=fog_transform.viewport_center_x=240;
        fog_transform.viewport_scale_y=fog_transform.viewport_center_y=136;
        std::array<vcs::GeGpuVertex,3> fog_model{};
        for(unsigned n=0;n<3;++n){fog_model[n].x=fog_positions[n][0];fog_model[n].y=fog_positions[n][1];fog_model[n].z=fog_positions[n][2];}
        const std::array<unsigned,3> fog_indices{0,1,2};
        auto check_fog_frame=[&](unsigned frame){
            check(vcs::ge_gpu_backend_finish_color_frame(frame),"GPU model-space fog frame");
            const auto image=vcs::ge_gpu_backend_game_frame_rgba();
            auto red=[&](unsigned x){return std::to_integer<unsigned>(image[(50*1280+x)*4]);};
            std::cout<<"fog frame "<<frame<<" samples "<<red(512)<<' '<<red(704)<<' '<<red(832)<<' '<<red(1088)<<'\n';
            check(red(512)<=2&&red(1088)>=253,"Model-space fog must preserve full boundary regions");
            check(red(704)>=48&&red(704)<=55&&red(832)>=150&&red(832)<=157,"Model-space fog must clamp after interpolation");
        };
        vcs::ge_gpu_backend_accumulate_hardware_triangles(fog_draw,fog_transform,fog_model,fog_indices);
        check_fog_frame(7);
        std::array<std::byte,30> fog_packed{};
        const std::array<std::array<int,3>,3> packed_positions{{{-32767,-32767,-16384},{32767,-32767,16384},{-32767,32767,-16384}}};
        for(unsigned n=0;n<3;++n){fog_packed[n*10+2]=fog_packed[n*10+3]=std::byte{255};
            for(unsigned k=0;k<3;++k){const unsigned v=static_cast<unsigned>(packed_positions[n][k])&65535;
                fog_packed[n*10+4+k*2]=std::byte(v&255);fog_packed[n*10+5+k*2]=std::byte(v>>8);
            }
        }
        fog_transform.fog_slope=4;fog_transform.primitive=3;
        check(vcs::ge_gpu_backend_accumulate_hardware_packed_0115(fog_draw,fog_transform,fog_packed,3,fog_indices),"Packed GPU fog path must be supported");
        check_fog_frame(8);
        // The software regression uses these same unequal clip-W vertices.
        // Exercise actual GPU interpolation rather than assuming both agree.
        transform.projection[11]=1;
        const std::array<std::array<float,3>,3> perspective_positions{{{-1,-1,0},{2,-2,1},{-1,1,0}}};
        for(unsigned n=0;n<3;++n){const auto p=vertices+n*16;
            memory.aot_store32(p,0xffffffff);
            for(unsigned k=0;k<3;++k)memory.aot_store32(p+4+k*4,std::bit_cast<unsigned>(perspective_positions[n][k]));
        }
        check(vcs::render_ge_primitive(memory,c,transform,vertices,0,(3<<16)|3,stats,error),error.c_str());
        check(vcs::ge_gpu_backend_finish_color_frame(9),"GPU unequal-W fog frame");
        const auto perspective_frame=vcs::ge_gpu_backend_game_frame_rgba();
        const auto perspective_red=std::to_integer<unsigned>(perspective_frame[(50*1280+640)*4]);
        std::cout<<"GPU unequal-W sample "<<perspective_red<<'\n';
        check(perspective_red>=83&&perspective_red<=88,"GPU fog must agree with software perspective interpolation");
        // CPU-written movie picture must overwrite stale GE color, retain its
        // shape/channels, stream on the next frame and stop when not submitted.
        const std::array<std::byte,32> movie{{std::byte{255},std::byte{0},std::byte{0},std::byte{255},
            std::byte{255},std::byte{0},std::byte{0},std::byte{255},std::byte{0},std::byte{255},std::byte{0},std::byte{255},
            std::byte{0},std::byte{255},std::byte{0},std::byte{255},std::byte{0},std::byte{0},std::byte{255},std::byte{255},
            std::byte{0},std::byte{0},std::byte{255},std::byte{255},std::byte{255},std::byte{255},std::byte{0},std::byte{255},
            std::byte{255},std::byte{255},std::byte{0},std::byte{255}}};
        world={};world.framebuffer_address=fb;world.framebuffer_stride=512;world.framebuffer_format=3;
        auto movie_stale=clear;for(auto& v:movie_stale)v.rgba=0xFFFF00FF;
        vcs::ge_gpu_backend_record_draw(world);vcs::ge_gpu_backend_accumulate_color_triangles(world,movie_stale);
        check(!renegade::movie105::queue_picture(fb,0,2,movie),"Movie rejects zero extent");
        check(!renegade::movie105::queue_picture(fb,4,2,std::span(movie).first(4)),"Movie rejects truncated picture");
        check(renegade::movie105::queue_picture(fb,4,2,movie),"Movie upload should queue");
        check(vcs::ge_gpu_backend_finish_color_frame(10),"Movie actual GPU frame");
        auto movie_rgb=[&](unsigned x,unsigned y){const auto image=vcs::ge_gpu_backend_game_frame_rgba();const auto p=(y*1280+x)*4;
            return std::to_integer<unsigned>(image[p])|(std::to_integer<unsigned>(image[p+1])<<8)|(std::to_integer<unsigned>(image[p+2])<<16);};
        check(movie_rgb(10,10)==0&&movie_rgb(10,710)==0,"Movie must retain black letterbox margins");
        check(movie_rgb(320,200)==0x0000ff&&movie_rgb(960,200)==0x00ff00,"Movie top row orientation/red-green channels");
        check(movie_rgb(320,520)==0xff0000&&movie_rgb(960,520)==0x00ffff,"Movie bottom row orientation/blue-yellow channels");
        auto next=movie;for(unsigned i=0;i<next.size();i+=4){next[i]=std::byte{12};next[i+1]=std::byte{34};next[i+2]=std::byte{56};}
        check(renegade::movie105::queue_picture(fb,4,2,next),"Changed movie picture queues");
        check(vcs::ge_gpu_backend_finish_color_frame(11),"Changed movie GPU frame");
        check(movie_rgb(640,360)==0x38220c,"Movie upload must refresh content under the same host identity");
        vcs::ge_gpu_backend_record_draw(world);vcs::ge_gpu_backend_accumulate_color_triangles(world,movie_stale);
        check(vcs::ge_gpu_backend_finish_color_frame(12),"Gameplay returns after movie");
        check(movie_rgb(640,360)==0xff00ff,"No movie submission must not overwrite the next GE frame");
        std::cout<<"CPU movie GPU presentation: aspect/channels/stream refresh/GE return passed at1280x720\n";
        vcs::shutdown_ge_gpu_backend();std::filesystem::remove_all(dir);
        std::cout<<"DX12 replacement, projected depth, stencil clipping/operations, fog boundaries (GE/prepared, model-space, packed), RAM/VRAM identity, alpha and dumps passed at 1280x720\n";return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';vcs::shutdown_ge_gpu_backend();std::filesystem::remove_all(dir);return 1;}
}
