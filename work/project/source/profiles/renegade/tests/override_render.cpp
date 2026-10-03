#include "../host/override_store.hpp"
#include "../host/override_source_cache.hpp"
#include "../host/test_environment010.hpp"
#include "ge_renderer.hpp"
#include <bit>
#include <chrono>
#include <fstream>
#include <iostream>
#include <algorithm>
using namespace renegade::overrides;
int main(){
    auto dir=std::filesystem::temp_directory_path()/("renegade-render-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    try {
        std::filesystem::create_directories(dir/"textures");
        renegade::test010::set_environment("RENEGADE_OVERRIDE_ROOT",dir.string().c_str());
        renegade::test010::set_environment("RENEGADE_DUMP_TEXTURES",(dir/"dump").string().c_str());
        std::vector<std::uint8_t> original{255,0,0,255};
        auto id=texture_id(1,1,original);
        auto check=[](bool ok,const char* why){if(!ok)throw std::runtime_error(why);};
        SourceTextureCache cache;SourceTextureCache::Key key{};
        std::vector<std::uint8_t> source_bytes(8192),palette_bytes(1024);unsigned decodes=0;
        auto decode=[&]() -> std::shared_ptr<const Texture>{++decodes;return {};};
        cache.lookup(key,source_bytes,palette_bytes,decode);
        cache.lookup(key,source_bytes,palette_bytes,decode);
        check(decodes==1&&cache.hits==1,"Unchanged sources bypass decode and canonical SHA");
        source_bytes[4137]=1;cache.lookup(key,source_bytes,palette_bytes,decode);
        check(decodes==2,"Single unsampled interior byte invalidates source cache");
        palette_bytes[999]=1;cache.lookup(key,source_bytes,palette_bytes,decode);
        check(decodes==3,"Palette-only edit invalidates cache");
        key[4]=5;cache.lookup(key,source_bytes,palette_bytes,decode);
        check(decodes==4,"Decode format participates in cache identity");
        auto owned=std::make_shared<Texture>();key[0]=1;
        cache.lookup(key,source_bytes,palette_bytes,[&](){++decodes;return owned;});
        owned.reset();cache.lookup(key,source_bytes,palette_bytes,decode);
        check(decodes==6,"Expired positive handle rechecks Store instead of becoming a negative hit");
        check(id.size()==71,"SHA256 identity length");
        std::vector<unsigned char> tga(18);tga[2]=2;tga[12]=3;tga[14]=1;tga[16]=32;tga[17]=0x28;
        // Higher-resolution non-power-of-two replacement: green, blue, white.
        tga.insert(tga.end(),{0,255,0,255,255,0,0,255,255,255,255,255});
        {std::ofstream f(dir/"textures"/(id+".tga"),std::ios::binary);f.write(reinterpret_cast<char*>(tga.data()),tga.size());}
        psprecomp::GuestMemory memory;std::array<std::uint32_t,256> c{};vcs::GeTransformState transform{};
        vcs::reset_ge_transform_state(transform);
        constexpr unsigned vertices=0x08801000,texture=0x08810000,fb=0x04000000;
        c[0x9d]=8;c[0xd2]=3;c[0xd5]=3|(3<<10);c[0x12]=0x800000|3|(7<<2)|(3<<7);
        c[0x1e]=1;c[0xa0]=texture&0xffffff;c[0xa8]=0x080001;c[0xc3]=3;c[0xc9]=3;c[0xde]=1;
        memory.aot_store32(texture,0xff0000ff);
        memory.aot_store32(vertices,std::bit_cast<unsigned>(0.5f));memory.aot_store32(vertices+4,0);
        memory.aot_store32(vertices+8,0xffffffff);
        for(unsigned offset:{12,16,20})memory.aot_store32(vertices+offset,0);
        vcs::GeRenderStats stats{};std::string error;
        check(vcs::render_ge_primitive(memory,c,transform,vertices,0,1,stats,error),error.c_str());
        check((memory.aot_load32(fb)&0xffffff)==0xff0000,"Real software draw samples higher-resolution blue replacement");
        check(memory.aot_load32(texture)==0xff0000ff,"Guest texture unchanged");
        check(std::filesystem::is_regular_file(dir/"dump"/(id+".tga")),"Discovery image exists");
        // Reuse the guest address for different content; no stale replacement.
        memory.aot_store32(texture,0xff00ffff);memory.aot_store32(fb,0);
        check(vcs::render_ge_primitive(memory,c,transform,vertices,0,1,stats,error),error.c_str());
        check((memory.aot_load32(fb)&0xffffff)==0x00ffff,"Changed content falls back to original yellow");
        // Index bytes stay unchanged while only the CLUT changes.
        constexpr unsigned palette=0x08812000;
        c[0xc3]=5;c[0xb0]=palette&0xffffff;c[0xb1]=0x080000;c[0xc5]=3|(255<<8);
        memory.aot_store32(texture,0);memory.aot_store32(palette,0xff0000ff);
        check(vcs::render_ge_primitive(memory,c,transform,vertices,0,1,stats,error),"Indexed render");
        check((memory.aot_load32(fb)&0xffffff)==0xff0000,"Indexed red finds same canonical replacement");
        memory.aot_store32(palette,0xff00ffff);
        check(vcs::render_ge_primitive(memory,c,transform,vertices,0,1,stats,error),"Changed palette render");
        check((memory.aot_load32(fb)&0xffffff)==0x00ffff,"Palette edit cannot retain stale replacement");
        // A late swizzled row must be covered by the source snapshot.
        auto swizzle_id=texture_id(8,16,std::vector<std::uint8_t>(8*16*4));
        auto red_tga=std::vector<unsigned char>(18);red_tga[2]=2;red_tga[12]=1;red_tga[14]=1;red_tga[16]=32;red_tga[17]=0x28;
        red_tga.insert(red_tga.end(),{0,0,255,255});
        {std::ofstream f(dir/"textures"/(swizzle_id+".tga"),std::ios::binary);f.write(reinterpret_cast<char*>(red_tga.data()),red_tga.size());}
        for(unsigned i=0;i<512;i+=4)memory.aot_store32(texture+i,0);
        c[0xc3]=3;c[0xc2]=1;c[0xb8]=3|(4<<8);c[0xa8]=0x080008;
        memory.aot_store32(vertices,std::bit_cast<unsigned>(7.f));memory.aot_store32(vertices+4,std::bit_cast<unsigned>(8.f));
        check(vcs::render_ge_primitive(memory,c,transform,vertices,0,1,stats,error),"Swizzled render");
        check((memory.aot_load32(fb)&0xffffff)==0xff,"Swizzled original finds red replacement");
        memory.aot_store32(texture+396,0xff00ffff);
        check(vcs::render_ge_primitive(memory,c,transform,vertices,0,1,stats,error),"Swizzle mutation render");
        check((memory.aot_load32(fb)&0xffffff)==0x00ffff,"Late swizzle block edit invalidates replacement");
        // Every supported GE source encoding, from VRAM and RAM, follows the
        // same content lookup even when no RSCF/model resource exists.
        c[0xc2]=0;c[0xb8]=0;c[0xc5]=3|(255<<8);
        // The existing PSP DXT decoder expands the 5-bit red endpoint to 248.
        // Content IDs deliberately preserve those decoded bytes.
        const auto dxt_id=texture_id(1,1,std::vector<std::uint8_t>{248,0,0,255});
        {std::ofstream f(dir/"textures"/(dxt_id+".tga"),std::ios::binary);f.write(reinterpret_cast<char*>(tga.data()),tga.size());}
        memory.aot_store32(palette,0xff0000ff);
        memory.aot_store32(vertices,std::bit_cast<unsigned>(0.5f));
        memory.aot_store32(vertices+4,0);
        for(unsigned base:{0x04010000u,0x08818000u})for(unsigned format=0;format<=10;++format){
            for(unsigned n=0;n<16;++n)memory.aot_store8(base+n,0);
            if(format==0)memory.aot_store16(base,0x001f); // PSP 565 red
            if(format==1)memory.aot_store16(base,0x801f); // 5551
            if(format==2)memory.aot_store16(base,0xf00f); // 4444
            if(format==3)memory.aot_store32(base,0xff0000ff);
            if(format>=8){memory.aot_store16(base+4,0xf800); // S3TC 565 red
                if(format==9)for(unsigned n=8;n<16;++n)memory.aot_store8(base+n,255);
                if(format==10)memory.aot_store8(base+14,255);
            }
            c[0xa0]=base&0xffffff;c[0xa8]=((base>>8)&0x0f0000)|1;c[0xc3]=format;
            memory.aot_store32(fb,0);
            check(vcs::render_ge_primitive(memory,c,transform,vertices,0,1,stats,error),"All-format source draw");
            if((memory.aot_load32(fb)&0xffffff)!=0xff0000)
                throw std::runtime_error("Texture format "+std::to_string(format)+" at "+std::to_string(base)+" yielded "+std::to_string(memory.aot_load32(fb)&0xffffff));
        }
        // HUD/menu sprite rectangle uses the same VRAM replacement path.
        c[0xc3]=3;c[0xa0]=0x010000;c[0xa8]=0x040001;
        memory.aot_store32(0x04010000,0xff0000ff);
        for(unsigned n=0;n<24;n+=4)memory.aot_store32(vertices+24+n,memory.aot_load32(vertices+n));
        memory.aot_store32(vertices+24+12,std::bit_cast<unsigned>(3.f));
        memory.aot_store32(vertices+24+16,std::bit_cast<unsigned>(3.f));
        for(unsigned n=0;n<64;++n)memory.aot_store32(fb+n*4,0);
        check(vcs::render_ge_primitive(memory,c,transform,vertices,0,(6<<16)|2,stats,error),"VRAM HUD rectangle");
        check((memory.aot_load32(fb+8*4+4)&0xffffff)==0xff0000,"HUD rectangle receives global replacement");
        // Explicit nonzero mip selection uses that level's content and records it.
        c[0xc2]=1<<16;c[0xc6]=4;c[0xc8]=1|(16<<16);
        c[0xa1]=0x818000;c[0xa9]=0x080001;c[0xb9]=0;
        memory.aot_store32(0x08818000,0xff0000ff);
        memory.aot_store32(fb,0);
        check(vcs::render_ge_primitive(memory,c,transform,vertices,0,1,stats,error),"Selected mip draw");
        check((memory.aot_load32(fb)&0xffffff)==0xff0000,"Selected mip receives its own content replacement");
        std::ifstream manifest(dir/"dump/textures.jsonl");
        std::string contents((std::istreambuf_iterator<char>(manifest)),{});
        manifest.close();
        check(contents.find("\"address\":67174400")!=std::string::npos,"Discovery records VRAM source provenance");
        check(contents.find("\"format\":10")!=std::string::npos,"Discovery records DXT5 source encoding");
        check(contents.find("\"mip_level\":1")!=std::string::npos,"Discovery records selected mip level");
        // The source dimension limit agrees with the public texture ID limit.
        std::vector<std::uint8_t> wide(4096*4);
        for(unsigned n=0;n<4096;++n){wide[n*4]=wide[n*4+3]=255;memory.aot_store32(0x04010000+n*4,0xff0000ff);}
        auto wide_tga=red_tga;wide_tga[18]=255;wide_tga[20]=0;
        {std::ofstream f(dir/"textures"/(texture_id(4096,1,wide)+".tga"),std::ios::binary);f.write(reinterpret_cast<char*>(wide_tga.data()),wide_tga.size());}
        c[0xc2]=0;c[0xc6]=0;c[0xc8]=0;c[0xb8]=12;
        check(vcs::render_ge_primitive(memory,c,transform,vertices,0,1,stats,error),"4096-wide source draw");
        check((memory.aot_load32(fb)&0xffffff)==0xff0000,"4096-wide source can be replaced");
        // A one-PSP-pixel rectangle must sample three independent replacement
        // texels in the 720p target, not enlarge its single guest VRAM sample.
        renegade::test010::set_environment("RENEGADE_HD_CAPTURE","1");
        renegade::test010::set_environment("RENEGADE_HD_SURFACE_TEXTURES","1");
        renegade::test010::set_environment("RENEGADE_HD_START_VBLANK","0");
        vcs::ge_hd_frame_boundary(1);
        vcs::ge_set_texture_inspection(true,0,0);
        c={};c[0x9d]=512;c[0xd2]=3;c[0xd5]=479|(271<<10);
        c[0x12]=0x800000|3|(7<<2)|(3<<7);c[0x1e]=1;
        c[0xa0]=texture&0xffffff;c[0xa8]=0x080001;c[0xc3]=3;c[0xc9]=3;c[0xde]=1;
        memory.aot_store32(texture,0xff0000ff);
        for(unsigned n=0;n<2;++n){
            const auto p=vertices+n*24;
            for(unsigned offset:{0,4,12,16})memory.aot_store32(p+offset,std::bit_cast<unsigned>(float(n)));
            memory.aot_store32(p+8,0xffffffff);memory.aot_store32(p+20,0);
        }
        check(vcs::render_ge_primitive(memory,c,transform,vertices,0,(6<<16)|2,stats,error),"HD rectangle");
        const auto hd=vcs::ge_hd_frame_rgb(fb,3);
        check(hd.size()==1280*720*3,"HD render dimensions");
        check(hd[0]==0&&hd[1]==255&&hd[2]==0,"HD first subpixel samples green");
        check(hd[3]==0&&hd[4]==0&&hd[5]==255,"HD second subpixel samples blue");
        check(hd[6]==255&&hd[7]==255&&hd[8]==255,"HD third subpixel samples white");
        const auto sharp_ui=vcs::ge_hd_frame_fxaa_rgb(fb,3);
        check(std::equal(hd.begin(),hd.begin()+9,sharp_ui.begin()),"FXAA preserves authored HUD samples exactly");
        const auto whole_frame_fxaa=vcs::ge_fxaa_rgb(hd,1280,720);
        check(!std::equal(hd.begin(),hd.begin()+9,whole_frame_fxaa.begin()),"Whole-frame FXAA would soften these HUD samples");
        check((memory.aot_load32(fb)&0xffffff)==0xff0000,"HD pass preserves original guest draw");
        // A second composition draw samples the HD surface, not the single blue
        // guest pixel. The native copy must remain low-resolution and unchanged.
        constexpr unsigned composed=0x04090000;
        const auto original_commands=c;
        c[0x9c]=composed&0x1fffff;c[0xa0]=fb&0xffffff;c[0xa8]=0x040200;c[0xb8]=9|(9<<8);
        check(vcs::render_ge_primitive(memory,c,transform,vertices,0,(6<<16)|2,stats,error),"HD surface composition");
        const auto composed_hd=vcs::ge_hd_frame_rgb(composed,3);
        check(composed_hd[0]==0&&composed_hd[1]==255&&composed_hd[2]==0,"Composition preserves first green HD subpixel");
        check(composed_hd[3]==0&&composed_hd[4]==0&&composed_hd[5]==255,"Composition preserves second blue HD subpixel");
        check(composed_hd[6]==255&&composed_hd[7]==255&&composed_hd[8]==255,"Composition preserves third white HD subpixel");
        check((memory.aot_load32(composed)&0xffffff)==0xff0000,"Guest composition still reads guest blue pixel");
        check(vcs::ge_hd_frame_rgb(fb,3)==hd,"Composition cannot modify its source HD image");
        // A RAM texture with identical low address bits is not a VRAM surface.
        memory.aot_store32(0x08800000,0xff00ffff);
        c[0xa0]=0x800000;c[0xa8]=0x080200;
        check(vcs::render_ge_primitive(memory,c,transform,vertices,0,(6<<16)|2,stats,error),"RAM low-bit alias draw");
        const auto ram_hd=vcs::ge_hd_frame_rgb(composed,3);
        check(ram_hd[0]==255&&ram_hd[1]==255&&ram_hd[2]==0,"RAM texture does not inherit VRAM HD surface");
        c=original_commands;
        vcs::ge_hd_frame_boundary(2);
        const auto inspection=vcs::ge_texture_inspection_lines(fb);
        check(std::any_of(inspection.begin(),inspection.end(),[&](const auto& line){return line==id;}),"Probe reports canonical original ID for visible draw");
        check(std::any_of(inspection.begin(),inspection.end(),[](const auto& line){return line=="REPLACEMENT: 3 X 1";}),"Probe reports actual replacement dimensions");
        vcs::ge_set_texture_inspection(false);
        c[0x1e]=0;c[0x9e]=0x88000;c[0x9f]=512;c[0x23]=1;c[0xde]=1;
        c[0xd5]=1|(1<<10);
        auto triangle=[&](float z,unsigned color){
            for(unsigned n=0;n<3;++n){
                const auto p=vertices+n*24;
                memory.aot_store32(p+8,color);
                memory.aot_store32(p+12,std::bit_cast<unsigned>(n==1?3.f:0.f));
                memory.aot_store32(p+16,std::bit_cast<unsigned>(n==2?3.f:0.f));
                memory.aot_store32(p+20,std::bit_cast<unsigned>(z));
            }
            check(vcs::render_ge_primitive(memory,c,transform,vertices,0,(3<<16)|3,stats,error),"HD triangle");
        };
        triangle(10,0xff0000ff);c[0xde]=4;triangle(20,0xffff0000);
        const auto occluded=vcs::ge_hd_frame_rgb(fb,3);
        check(occluded[0]==255&&occluded[2]==0,"HD depth rejects farther triangle");
        check(occluded[6*3]==0&&occluded[6*3+1]==0&&occluded[6*3+2]==0,"HD scissor bounds preserved");
        triangle(5,0xff00ff00);
        const auto nearer=vcs::ge_hd_frame_rgb(fb,3);
        check(nearer[0]==0&&nearer[1]==255,"HD depth accepts nearer triangle");
        renegade::test010::set_environment("RENEGADE_HD_CAPTURE","0");
        vcs::ge_hd_frame_boundary(3);
        check(vcs::ge_hd_frame_rgb(fb,3).empty(),"Disabling HD clears shadow surfaces");
        const std::vector<std::uint8_t> flat(8*8*3,73);
        check(vcs::ge_fxaa_rgb(flat,8,8)==flat,"FXAA preserves a flat texture exactly");
        std::vector<std::uint8_t> edge(8*8*3);
        for(unsigned y=0;y<8;++y)for(unsigned x=0;x<8;++x)
            for(unsigned k=0;k<3;++k)edge[(y*8+x)*3+k]=x>y?255:0;
        const auto smooth=vcs::ge_fxaa_rgb(edge,8,8);
        check(smooth!=edge,"FXAA smooths a diagonal edge");
        check(smooth[(7*8)*3]==0&&smooth[7*3]==255,"FXAA preserves distant black and white regions");
        bool malformed=false;try{vcs::ge_fxaa_rgb({},8,8);}catch(const std::exception&){malformed=true;}
        check(malformed,"FXAA rejects incomplete image buffers");
        // Source RGB with guest alpha preserves alpha-test behavior, including
        // non-opaque material masks, without modifying either texture's bytes.
        const std::vector<std::uint8_t> alpha_source{200,20,10,64};
        const auto alpha_id=texture_id(1,1,alpha_source);
        {std::ofstream f(dir/"textures"/(alpha_id+".tga"),std::ios::binary);f.write(reinterpret_cast<char*>(tga.data()),tga.size());}
        {std::ofstream f(dir/"textures"/(alpha_id+".json"));f<<"{\"alpha\":\"original\"}\n";}
        auto alpha_replacement=find_texture(1,1,alpha_source);
        check(alpha_replacement&&alpha_replacement->use_original_alpha,"Original alpha policy loads");
        check(alpha_replacement->rgba[3]==255,"Policy preserves supplied image bytes");
        c={};c[0x9d]=8;c[0xd2]=3;c[0xd5]=3|(3<<10);
        c[0x12]=0x800000|3|(7<<2)|(3<<7);c[0x1e]=1;
        c[0xa0]=texture&0xffffff;c[0xa8]=0x080001;c[0xc3]=3;c[0xc9]=3;c[0xde]=1;
        c[0xc9]=3|(1<<8);c[0x22]=1;c[0xdb]=2|(64<<8)|(255<<16);
        memory.aot_store32(texture,0x400a14c8);memory.aot_store32(fb,0);
        for(unsigned offset:{0,4,12,16,20})memory.aot_store32(vertices+offset,0);
        memory.aot_store32(vertices+8,0xffffffff);
        check(vcs::render_ge_primitive(memory,c,transform,vertices,0,1,stats,error),"Guest alpha draw");
        check((memory.aot_load32(fb)&0xffffff)==0x00ff00,"Replacement green passes original-alpha test");
        c[0xdb]=2|(255<<8)|(255<<16);memory.aot_store32(fb,0);
        check(vcs::render_ge_primitive(memory,c,transform,vertices,0,1,stats,error),"Guest alpha rejection draw");
        check(memory.aot_load32(fb)==0,"Source opaque alpha does not override guest alpha rejection");
        Texture mesh_image;std::string mesh_error;
        check(load_texture(dir/"textures"/(alpha_id+".tga"),mesh_image,mesh_error)&&!mesh_image.use_original_alpha,
              "Direct mesh-bound image load ignores global sidecar policy");
        const std::vector<std::uint8_t> bad_source{201,20,10,64};const auto bad_id=texture_id(1,1,bad_source);
        {std::ofstream f(dir/"textures"/(bad_id+".tga"),std::ios::binary);f.write(reinterpret_cast<char*>(tga.data()),tga.size());}
        {std::ofstream f(dir/"textures"/(bad_id+".json"));f<<"{\"alpha\":\"typo\"}";}
        check(!find_texture(1,1,bad_source),"Invalid policy retains original texture");
        check(!find_texture(1,1,bad_source),"Invalid policy failure is cached");
        // An unavailable dump destination cannot cancel an otherwise valid pack.
        std::filesystem::remove_all(dir/"dump");
        {std::ofstream block(dir/"dump");block<<"not a directory";}
        const std::vector<std::uint8_t> distinct{1,2,3,255};
        {std::ofstream f(dir/"textures"/(texture_id(1,1,distinct)+".tga"),std::ios::binary);f.write(reinterpret_cast<char*>(wide_tga.data()),wide_tga.size());}
        auto surviving=find_texture(1,1,distinct);
        check(surviving&&surviving->rgba[2]==255,"Dump failure preserves valid replacement");
        std::filesystem::remove_all(dir);std::cout<<"Override render integration passed\n";return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';std::filesystem::remove_all(dir);return 1;}
}
