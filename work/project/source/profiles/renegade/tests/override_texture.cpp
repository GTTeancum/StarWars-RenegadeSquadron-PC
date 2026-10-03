#include "../host/override_texture.hpp"
#include <chrono>
#include <fstream>
#include <iostream>
#include <vector>
using namespace renegade::overrides;
using Bytes = std::vector<std::uint8_t>;
void put32(Bytes& b, std::size_t at, std::uint32_t v) {
    for (unsigned i=0;i<4;++i) b.at(at+i)=static_cast<std::uint8_t>(v>>(8*i));
}
int main() {
    auto directory=std::filesystem::temp_directory_path() / ("renegade-image-test-" +
        std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    std::filesystem::create_directories(directory);
    unsigned checks=0, failures=0;
    auto check=[&](bool ok,const char* why){ ++checks; if(!ok){++failures;std::cerr<<why<<'\n';} };
    Texture texture; std::string error;
    auto load=[&](const char* name,const Bytes& bytes) {
        auto path=directory/name;
        {std::ofstream f(path,std::ios::binary);f.write(reinterpret_cast<const char*>(bytes.data()),bytes.size());}
        return load_texture(path,texture,error);
    };
    // Two rows distinguish orientation, RGBA channels and alpha preservation.
    Bytes tga(18);tga[2]=2;tga[12]=1;tga[14]=2;tga[16]=32;tga[17]=0x28;
    tga.insert(tga.end(),{0,0,255,128,0,255,0,255});
    check(load("pixels.TGA",tga),"TGA decode");
    const Bytes expected{255,0,0,128,0,255,0,255};
    check(texture.width==1&&texture.height==2&&texture.rgba==expected,"TGA orientation and alpha");
    tga[17]=8;
    std::swap_ranges(tga.begin()+18,tga.begin()+22,tga.begin()+22);
    check(load("bottom.tga",tga)&&texture.rgba==expected,"Bottom-origin TGA");
    tga[2]=10;tga.insert(tga.begin()+18,1);
    check(load("rle.tga",tga)&&texture.rgba==expected,"RLE TGA");
    Bytes dds(128);dds[0]='D';dds[1]='D';dds[2]='S';dds[3]=' ';
    put32(dds,4,124);put32(dds,8,0x100f);put32(dds,12,2);put32(dds,16,1);put32(dds,20,4);
    put32(dds,76,32);put32(dds,80,0x41);put32(dds,88,32);
    put32(dds,92,0xff);put32(dds,96,0xff00);put32(dds,100,0xff0000);put32(dds,104,0xff000000);put32(dds,108,0x1000);
    dds.insert(dds.end(),expected.begin(),expected.end());
    check(load("pixels.dds",dds)&&texture.rgba==expected,"RGBA DDS");
    Bytes bc1(dds.begin(),dds.begin()+128);put32(bc1,8,0x81007);put32(bc1,12,4);put32(bc1,16,4);put32(bc1,20,8);
    put32(bc1,80,4);put32(bc1,84,0x31545844);put32(bc1,88,0);
    bc1.insert(bc1.end(),{0,248,0,0,0,0,0,0});
    check(load("bc1.dds",bc1)&&texture.width==4&&texture.height==4,"BC1 DDS");
    bool red=texture.rgba.size()==64;
    for(std::size_t i=0;red&&i<64;i+=4) red=texture.rgba[i]==255&&texture.rgba[i+1]==0&&texture.rgba[i+2]==0&&texture.rgba[i+3]==255;
    check(red,"BC1 red block colors");
    // Independent BC2/BC3 blocks exercise every alpha selector in raster order.
    // Endpoint differences are divisible by 5/7 to avoid rounding ambiguity.
    Bytes bc3(bc1.begin(),bc1.begin()+128);put32(bc3,20,16);put32(bc3,84,0x35545844);
    bc3.insert(bc3.end(),{210,70,0,0,0,0,0,0,0,248,0,0,0,0,0,0});
    std::uint64_t selectors=0;for(unsigned i=0;i<16;++i)selectors|=std::uint64_t(i%8)<<(i*3);
    for(unsigned i=0;i<6;++i)bc3[130+i]=selectors>>(i*8);
    auto alpha_matches=[&](const std::vector<unsigned>& alpha){
        if(texture.rgba.size()!=64)return false;
        for(unsigned i=0;i<16;++i)if(texture.rgba[i*4]!=255||texture.rgba[i*4+1]!=0||
            texture.rgba[i*4+2]!=0||texture.rgba[i*4+3]!=alpha[i%alpha.size()])return false;
        return true;
    };
    check(load("bc3-eight.dds",bc3)&&alpha_matches({210,70,190,170,150,130,110,90}),
          "BC3 eight-alpha mode preserves RGB and every interpolated alpha selector");
    bc3[128]=10;bc3[129]=110;
    check(load("bc3-six.dds",bc3)&&alpha_matches({10,110,30,50,70,90,0,255}),
          "BC3 six-alpha mode preserves transparent and opaque special selectors");
    auto before_truncation=texture.rgba;bool truncated=true;
    for(unsigned n=128;n<144;++n){auto short_block=bc3;short_block.resize(n);
        truncated&=!load("bc3-truncated.dds",short_block)&&texture.rgba==before_truncation;}
    check(truncated,"Every incomplete BC3 block rejects without replacing prior pixels");
    Bytes bc2=bc3;put32(bc2,84,0x33545844);
    for(unsigned i=0;i<8;++i)bc2[128+i]=(2*i)|((2*i+1)<<4);
    check(load("bc2.dds",bc2)&&alpha_matches({0,17,34,51,68,85,102,119,136,153,170,187,204,221,238,255}),
          "BC2 explicit four-bit alpha expands all sixteen levels");
    // Independent 1x2 RGBA PNG fixture (zlib-compressed scanlines).
    const Bytes png{137,80,78,71,13,10,26,10,0,0,0,13,73,72,68,82,0,0,0,1,0,0,0,2,8,6,0,0,0,153,129,182,39,0,0,0,18,73,68,65,84,120,156,99,248,207,192,208,192,192,240,159,225,63,0,15,253,3,126,249,223,138,13,0,0,0,0,73,69,78,68,174,66,96,130};
    check(load("pixels.png",png)&&texture.rgba==expected,"PNG RGBA and alpha");
    const auto saved=texture.rgba;
    check(!load("bad.png",Bytes{1,2,3})&&!error.empty()&&texture.rgba==saved,"Malformed PNG preserves output");
    check(!load("bad.dds",Bytes{'D','D','S',' '})&&texture.rgba==saved,"Truncated DDS preserves output");
    check(!load("bad.tga",Bytes{0,0,2})&&texture.rgba==saved,"Truncated TGA preserves output");
    check(!load("bad.jpg",png),"Unsupported extension");
    check(!load_texture(directory/"absent.png",texture,error),"Missing file");
    std::filesystem::remove_all(directory);
    std::cout<<checks<<" checks, "<<failures<<" failures\n";
    return failures?1:0;
}
