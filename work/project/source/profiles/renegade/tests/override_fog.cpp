#include "../host/test_environment010.hpp"
#include "ge_renderer.hpp"
#include <array>
#include <bit>
#include <iostream>
#include <stdexcept>

int main() {
    try {
        renegade::test010::set_environment("RENEGADE_HD_CAPTURE", "0");
        psprecomp::GuestMemory memory;
        std::array<std::uint32_t,256> c{};
        vcs::GeTransformState transform{};
        vcs::GeRenderStats stats{};
        std::string error;
        constexpr unsigned vertices=0x08801000, texture=0x08810000, fb=0x04000000;
        auto check=[](bool ok,const char* why){if(!ok)throw std::runtime_error(why);};
        auto float24=[](float value){return std::bit_cast<unsigned>(value)>>8;};
        auto setup=[&] {
            c={}; c[0x9d]=512; c[0xd2]=3; c[0xd5]=479|(271<<10);
            c[0x12]=(7<<2)|(3<<7); c[0x1f]=1;
            c[0x42]=c[0x45]=float24(240); c[0x43]=c[0x46]=float24(136);
            c[0xce]=float24(1);
            vcs::reset_ge_transform_state(transform); transform.projection[10]=0;
        };
        auto vertex=[&](unsigned n,float x,float y,float z,unsigned color=0xffffffff) {
            const auto p=vertices+n*16;
            memory.aot_store32(p,color);
            for(unsigned k=0;k<3;++k)memory.aot_store32(p+4+k*4,
                std::bit_cast<unsigned>(std::array<float,3>{x,y,z}[k]));
        };
        auto triangle=[&](unsigned color=0xffffffff) {
            vertex(0,-1,-1,-2,color); vertex(1,1,-1,2,color); vertex(2,-1,1,-2,color);
        };
        auto draw=[&](unsigned primitive,unsigned count) {
            check(vcs::render_ge_primitive(memory,c,transform,vertices,0,
                (primitive<<16)|count,stats,error),error.c_str());
        };
        auto pixel=[&](unsigned x,unsigned y){return memory.aot_load32(fb+(y*512+x)*4);};
        auto red=[&](unsigned x,unsigned y){return pixel(x,y)&255u;};
        setup(); triangle(); draw(3,3);
        std::cout<<"Native boundary samples "<<red(192,20)<<' '<<red(264,20)<<' '
                 <<red(312,20)<<' '<<red(408,20)<<'\n';
        check(red(192,20)<=2,"Software must apply full fog before the boundary");
        check(red(264,20)>=49&&red(264,20)<=54,"Software must interpolate raw fog before fragment clamping");
        check(red(312,20)>=151&&red(312,20)<=156,"Software must retain the fog gradient");
        check(red(408,20)>=253,"Software must preserve the clear region beyond fog");
        // Unequal clip W distinguishes perspective interpolation from a
        // screen-space ramp. At screen center these vertices produce ~1/3.
        transform.projection[11]=1;
        vertex(0,-1,-1,0); vertex(1,2,-2,1); vertex(2,-1,1,0); draw(3,3);
        std::cout<<"Native unequal-W sample "<<red(240,20)<<'\n';
        check(red(240,20)>=83&&red(240,20)<=88,"Fog must retain perspective interpolation when clip W differs");
        setup(); vertex(0,-2,-1,-2); vertex(1,1,-1,2); vertex(2,-2,1,-2); draw(3,3);
        std::cout<<"Native clipped samples "<<red(96,20)<<' '<<red(168,20)<<' '<<red(240,20)<<' '<<red(300,20)<<'\n';
        check(red(96,20)<=2&&red(168,20)>=66&&red(168,20)<=72&&
              red(240,20)>=168&&red(240,20)<=174&&red(300,20)>=253,
              "Clipped fog must preserve raw coefficients through new vertices");
        triangle();
        // Change ONLY each fog register, exercising the decoded-state cache.
        c[0xcf]=0x302010; draw(3,3);
        check((pixel(192,20)&0xffffff)==0x302010,"Fog color mutation must invalidate cached fragment state");
        c[0x1f]=0; draw(3,3);
        check((pixel(192,20)&0xffffff)==0xffffff,"Disabling fog must invalidate cached fragment state");
        c[0x1f]=1; draw(3,3);
        check((pixel(192,20)&0xffffff)==0x302010,"Re-enabling fog must restore the fog color");
        // Source alpha is used for rejection/blending, not replaced by fog.
        triangle(0x40ffffff); c[0x22]=1; c[0xdb]=2|(64<<8)|(255<<16);
        draw(3,3);
        check((pixel(192,20)&0xffffff)==0x302010,"Fog must preserve source alpha-test acceptance");
        c[0xdb]=2|(255<<8)|(255<<16); memory.aot_store32(fb+(20*512+192)*4,0x5a123456);
        draw(3,3);
        check(pixel(192,20)==0x5a123456,"Fog must preserve alpha rejection and destination stencil/alpha");
        c[0x22]=0; c[0x21]=1; c[0xdf]=2|(3<<4);
        memory.aot_store32(fb+(20*512+192)*4,0x5a000000); draw(3,3);
        check(pixel(192,20)==0x5a0c0804,"Fog RGB must blend using the unchanged source alpha");
        // A texture REPLACE draw must fog its sampled color, after texturing.
        setup(); c[0x1e]=1; c[0xa0]=texture&0xffffff; c[0xa8]=0x080001;
        c[0xc3]=3; c[0xc9]=3|(1<<8); c[0xcf]=0x302010;
        memory.aot_store32(texture,0x40ffffff); triangle(0xff000000);
        c[0x22]=1; c[0xdb]=2|(64<<8)|(255<<16); draw(3,3);
        check((pixel(408,20)&0xffffff)==0xffffff,"Texture REPLACE must precede fog");
        check((pixel(192,20)&0xffffff)==0x302010,"Textured fog preserves texture alpha-test acceptance");
        // Points/lines use their decoded/projected fog, independent of texture.
        setup(); c[0xcf]=0x302010; vertex(0,0,0,-2); draw(0,1);
        check((pixel(240,136)&0xffffff)==0x302010,"Projected point must receive fog");
        c[0xcf]=0; vertex(0,-1,-0.8f,-2); vertex(1,1,-0.8f,2); draw(1,2);
        check(red(192,27)<=2&&red(264,27)>=49&&red(264,27)<=54&&red(408,27)>=253,
              "Projected line must clamp interpolated raw fog");
        // Screen-space HUDs and clear operations bypass fog even when enabled.
        c[0x12]|=0x800000; c[0xcf]=0x302010;
        vertex(0,1,1,0,0xffa0b0c0); vertex(1,4,4,0,0xffa0b0c0); draw(6,2);
        check((pixel(2,2)&0xffffff)==0xa0b0c0,"Through-mode sprite must remain unchanged by fog");
        vertex(0,1,1,0,0xffabcdef); draw(0,1);
        check((pixel(1,1)&0xffffff)==0xabcdef,"Through-mode point must bypass fog");
        c[0xd3]=1|0x100|0x200; vertex(0,1,1,0,0x40abcdef); vertex(1,4,4,0,0x40abcdef); draw(6,2);
        check(pixel(2,2)==0x40abcdef,"Clear must preserve requested color and alpha while fog is enabled");
        // Real 720p software surface, with the same boundary as the GPU fixture.
        renegade::test010::set_environment("RENEGADE_HD_CAPTURE","1");
        renegade::test010::set_environment("RENEGADE_HD_START_VBLANK","0");
        vcs::ge_hd_frame_boundary(1); setup(); triangle(); draw(3,3);
        const auto hd=vcs::ge_hd_frame_rgb(fb,3);
        check(hd.size()==1280*720*3,"Fog regression must use actual HD software rendering");
        auto hd_red=[&](unsigned x){return hd[(50*1280+x)*3];};
        std::cout<<"HD boundary samples "<<unsigned(hd_red(512))<<' '<<unsigned(hd_red(704))<<' '
                 <<unsigned(hd_red(832))<<' '<<unsigned(hd_red(1088))<<'\n';
        check(hd_red(512)<=2&&hd_red(704)>=48&&hd_red(704)<=55&&
              hd_red(832)>=150&&hd_red(832)<=157&&hd_red(1088)>=253,
              "HD software must retain both boundaries and gradient");
        transform.projection[11]=1;
        vertex(0,-1,-1,0); vertex(1,2,-2,1); vertex(2,-1,1,0); draw(3,3);
        const auto hd_perspective=vcs::ge_hd_frame_rgb(fb,3);
        const auto hd_center=hd_perspective[(50*1280+640)*3];
        std::cout<<"HD unequal-W sample "<<unsigned(hd_center)<<'\n';
        check(hd_center>=83&&hd_center<=88,"HD fog must preserve the perspective coefficient");
        std::cout<<"Software fog boundaries, cache state, texture order, alpha, points/lines, HUD/clear and real 720p passed\n";
        return 0;
    } catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
