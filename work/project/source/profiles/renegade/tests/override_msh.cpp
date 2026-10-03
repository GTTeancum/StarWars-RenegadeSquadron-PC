#include "../host/override_msh.hpp"
#include <bit>
#include <iostream>
#include <limits>
using namespace renegade::overrides;
using Bytes=std::vector<std::uint8_t>;
void u32(Bytes& b,std::uint32_t v){for(unsigned i=0;i<4;++i)b.push_back(static_cast<std::uint8_t>(v>>(i*8)));}
void u16(Bytes& b,std::uint16_t v){b.push_back(v&255);b.push_back(v>>8);}
void f32(Bytes& b,float f){u32(b,std::bit_cast<std::uint32_t>(f));}
Bytes integer(std::uint32_t v){Bytes b;u32(b,v);return b;}
Bytes string(const char* s){Bytes b;while(*s)b.push_back(*s++);b.push_back(0);while(b.size()%4)b.push_back(0);return b;}
void chunk(Bytes& b,const char* tag,const Bytes& data){b.insert(b.end(),tag,tag+4);u32(b,data.size());b.insert(b.end(),data.begin(),data.end());}
Bytes make(bool strips=false,bool cycle=false,bool bad_index=false,bool mismatch=false,bool nan=false,bool skin=false) {
    Bytes seg,pos;u32(pos,4);
    for(float x:{0.f,0.f,0.f,1.f,0.f,0.f,0.f,1.f,0.f,1.f,1.f,0.f})f32(pos,nan?std::numeric_limits<float>::quiet_NaN():x);
    chunk(seg,"POSL",pos);chunk(seg,"MATI",integer(0));chunk(seg,"CLRB",integer(0xff80ffff));
    Bytes uv;u32(uv,mismatch?3:4);for(unsigned i=0;i<(mismatch?6:8);++i)f32(uv,float(i%2));chunk(seg,"UV0L",uv);
    Bytes tris;u32(tris,strips?4:2);
    if(strips){for(auto i:{0x8000,0x8001,2,3})u16(tris,i);chunk(seg,"STRP",tris);}
    else {for(auto i:{0,1,2,2,1,bad_index?9:3})u16(tris,i);chunk(seg,"NDXT",tris);}
    if(skin){Bytes w;u32(w,4);for(unsigned i=0;i<16;++i){u32(w,0);f32(w,i%4?0.f:1.f);}chunk(seg,"WGHT",w);}
    Bytes geom;chunk(geom,"SEGM",seg);if(skin){Bytes env;u32(env,1);u32(env,1);chunk(geom,"ENVL",env);}
    Bytes model;chunk(model,"MNDX",integer(1));chunk(model,"MTYP",integer(skin?1:4));chunk(model,"NAME",string("mesh"));
    if(cycle)chunk(model,"PRNT",string("mesh"));
    Bytes tran;for(float x:{2.f,3.f,4.f,0.f,0.f,0.f,1.f,10.f,20.f,30.f})f32(tran,x);
    chunk(model,"TRAN",tran);chunk(model,"GEOM",geom);
    Bytes mat;chunk(mat,"NAME",string("material"));chunk(mat,"TX0D",string("diffuse.tga"));chunk(mat,"ATRB",Bytes{4,0,0,0});
    Bytes mats;u32(mats,1);chunk(mats,"MATD",mat);
    Bytes scene;chunk(scene,"MATL",mats);chunk(scene,"MODL",model);chunk(scene,"TEST",Bytes{1,2,3});
    Bytes root;chunk(root,"MSH2",scene);chunk(root,"CL1L",{});
    Bytes file;chunk(file,"HEDR",root);return file;
}
int main(){
    unsigned checks=0,failed=0;auto check=[&](bool ok,const char* why){++checks;if(!ok){++failed;std::cerr<<why<<'\n';}};
    MshScene scene;std::string error;
    auto data=make();check(parse_msh(data,scene,error),"Classic MSH parsing");
    if(scene.nodes.empty())return 1;
    check(scene.materials.size()==1&&scene.materials[0].textures[0]=="diffuse.tga","Texture reference");
    check(scene.nodes[0].scale==std::array<float,3>{2,3,4}&&scene.nodes[0].translation[2]==30,"MSH transforms");
    check(scene.nodes[0].segments[0].triangles.size()==2&&scene.nodes[0].segments[0].colors.size()==4,"Triangle and constant color expansion");
    check(parse_msh(make(true),scene,error)&&scene.nodes[0].segments[0].triangles[1]==std::array<std::uint32_t,3>{2,1,3},"Strip winding");
    check(parse_msh(make(false,false,false,false,false,true),scene,error)&&scene.nodes[0].segments[0].weights.size()==4,"Skin weights and envelope");
    check(!parse_msh(make(false,true),scene,error),"Reject hierarchy cycle");
    check(!parse_msh(make(false,false,true),scene,error),"Reject bad vertex index");
    check(!parse_msh(make(false,false,false,true),scene,error),"Reject UV mismatch");
    check(!parse_msh(make(false,false,false,false,true),scene,error),"Reject nonfinite coordinates");
    check(scene.nodes.size()==1&&scene.nodes[0].segments[0].weights.size()==4,"Failed parse preserves output");
    bool rejected=true;
    for(std::size_t n=0;n<data.size();++n)if(parse_msh(std::span(data).first(n),scene,error)){rejected=false;break;}
    check(rejected,"Reject every truncation of valid fixture");
    data[4]=255;data[5]=255;data[6]=255;data[7]=255;
    check(!parse_msh(data,scene,error),"Reject overflowing root length");
    check(!load_msh("nonexistent-override-model.msh",scene,error),"Missing model file");
    auto material_file=[](const Bytes& payload,bool duplicate=false){
        Bytes mat;chunk(mat,"DATA",payload);if(duplicate)chunk(mat,"DATA",payload);
        Bytes mats;u32(mats,1);chunk(mats,"MATD",mat);
        Bytes node;chunk(node,"NAME",string("material-test"));chunk(node,"MNDX",integer(1));
        Bytes scene;chunk(scene,"MATL",mats);chunk(scene,"MODL",node);Bytes root;chunk(root,"MSH2",scene);
        Bytes file;chunk(file,"HEDR",root);return file;
    };
    Bytes values;for(unsigned i=0;i<13;++i)f32(values,float(i)*0.125f);
    check(parse_msh(material_file(values),scene,error)&&scene.materials[0].has_data&&
          scene.materials[0].diffuse[3]==0.375f&&scene.materials[0].specular[0]==0.5f&&
          scene.materials[0].ambient[3]==1.375f&&scene.materials[0].specular_exponent==1.5f,
          "Material DATA retains distinct RGBA channels and exponent");
    auto saved=scene.materials[0].specular;
    check(!parse_msh(material_file(values,true),scene,error)&&scene.materials[0].specular==saved,
          "Duplicate material DATA rejects atomically");
    bool malformed=true;
    for(unsigned n=0;n<56;++n)if(n!=52){auto bytes=values;bytes.resize(n);malformed&=!parse_msh(material_file(bytes),scene,error);}
    check(malformed,"Material DATA rejects truncated and oversized payloads");
    bool nonfinite=true;
    for(unsigned i=0;i<13;++i){auto bad=values;auto bits=std::bit_cast<unsigned>(std::numeric_limits<float>::infinity());
        for(unsigned k=0;k<4;++k)bad[i*4+k]=static_cast<std::uint8_t>(bits>>(k*8));
        nonfinite&=!parse_msh(material_file(bad),scene,error);}
    check(nonfinite,"Every nonfinite material DATA field rejected");
    check(parse_msh(make(),scene,error)&&!scene.materials[0].has_data&&scene.materials[0].specular[0]==1,
          "Legacy fixture without DATA retains explicit defaults");
    std::cout<<checks<<" checks, "<<failed<<" failures\n";return failed?1:0;
}
