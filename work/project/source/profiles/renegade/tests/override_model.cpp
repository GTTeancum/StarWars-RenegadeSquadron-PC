#include "../host/override_model.hpp"
#include "../host/override_world.hpp"
#include "../host/override_skin.hpp"
#include "../host/override_store.hpp"
#include "../host/render_resource_trace024.hpp"
#include "../host/test_environment010.hpp"
#include "ge_renderer.hpp"
#include <bit>
#include <chrono>
#include <fstream>
#include <iostream>
using namespace renegade::overrides;
using B=std::vector<std::uint8_t>;
void u32(B& b,unsigned v){for(unsigned i=0;i<4;++i)b.push_back(v>>(i*8));}
void chunk(B& b,const char* tag,B d){b.insert(b.end(),tag,tag+4);u32(b,d.size());b.insert(b.end(),d.begin(),d.end());}
B number(unsigned n){B b;u32(b,n);return b;}
B text(const char* s){B b;while(*s)b.push_back(*s++);b.push_back(0);while(b.size()%4)b.push_back(0);return b;}
B fixture(const char* texture=nullptr,unsigned flags=8,unsigned color=0xff123456,unsigned render_type=0,std::array<float,3> specular={1,1,1},const char* normal=nullptr){
    B positions;u32(positions,4);
    for(float x:{-0.9f,-0.9f,0.f,0.9f,-0.9f,0.f,-0.9f,0.9f,0.f,0.9f,0.9f,0.f})u32(positions,std::bit_cast<unsigned>(x));
    B triangles;u32(triangles,2);for(unsigned x:{0,1,2,2,1,3}){triangles.push_back(x);triangles.push_back(0);}
    B segment;chunk(segment,"MATI",number(0));chunk(segment,"POSL",positions);chunk(segment,"NDXT",triangles);
    B uv;u32(uv,4);for(float value:{0.f,0.f,1.f,0.f,0.f,1.f,1.f,1.f})u32(uv,std::bit_cast<unsigned>(value));chunk(segment,"UV0L",uv);
    chunk(segment,"CLRB",number(texture?0xffffffff:color));
    B geometry;chunk(geometry,"SEGM",segment);
    B node;chunk(node,"NAME",text("replacement"));chunk(node,"MNDX",number(1));chunk(node,"MTYP",number(4));chunk(node,"GEOM",geometry);
    B material;chunk(material,"NAME",text("plain"));if(texture)chunk(material,"TX0D",text(texture));
    if(normal)chunk(material,"TX1D",text(normal));
    chunk(material,"ATRB",B{static_cast<std::uint8_t>(flags),static_cast<std::uint8_t>(render_type),0,0});
    B data;for(float v:{1.f,1.f,1.f,1.f,specular[0],specular[1],specular[2],1.f,1.f,1.f,1.f,1.f,50.f})u32(data,std::bit_cast<unsigned>(v));
    chunk(material,"DATA",data);
    B materials;u32(materials,1);chunk(materials,"MATD",material);
    B scene;chunk(scene,"MATL",materials);chunk(scene,"MODL",node);B root;chunk(root,"MSH2",scene);B file;chunk(file,"HEDR",root);return file;
}
int main(int argc,char** argv){
    if(argc==2&&std::string(argv[1])=="--registry-benchmark"){
        namespace rr=renegade::render_resources;psprecomp::GuestMemory memory;
        for(unsigned i=0;i<rr::capacity;++i){
            rr::Record r{"bench",0x08880004+i*32,i+1,0x08900000+i*64,0x08a00000+i*8,1,1,32};
            memory.aot_store32(r.record-4,r.key);memory.aot_store32(r.record+4,r.vertices);
            memory.aot_store32(r.record+8,r.indices);memory.aot_store32(r.record+16,r.vertex_count);
            memory.aot_store32(r.record+20,r.index_count);memory.aot_store8(r.record+24,0);
            rr::records[r.vertices]=r;
        }
        auto start=std::chrono::steady_clock::now();unsigned matches=0;
        for(unsigned i=0;i<10000;++i)matches+=rr::resolve_part(memory,0x08940000+(i%16)*32,0x08b00000,(4<<16)|3).resource!=nullptr;
        auto ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
        std::cout<<"{\"queries\":10000,\"records\":"<<rr::records.size()<<",\"matches\":"<<matches<<",\"milliseconds\":"<<ms<<"}\n";
        return matches?1:0;
    }
    auto directory=std::filesystem::temp_directory_path()/("renegade-model-test-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    unsigned checks=0;auto check=[&](bool ok,const char* why){++checks;if(!ok)throw std::runtime_error(why);};
    try{
        std::filesystem::create_directories(directory/"models/test/part-dir");
        std::filesystem::create_directories(directory/"textures");
        renegade::test010::set_environment("RENEGADE_OVERRIDE_ROOT",directory.string().c_str());
        auto bytes=fixture();{std::ofstream f(directory/"models/test/part-0.msh",std::ios::binary);f.write(reinterpret_cast<char*>(bytes.data()),bytes.size());}
        MshScene scene;Model model;std::string error;
        check(parse_msh(bytes,scene,error)&&compile_model(scene,model,error),"Compile classic MSH");
        check(model.segments.size()==1&&model.segments[0].vertices.size()==6,"Triangle list compilation");
        {
            auto shadow_scene=scene;shadow_scene.has_shadow_volumes=true;auto volume=scene.nodes[0];
            volume.name="shadow-volume";volume.index=2;volume.type=6;volume.segments[0].material=999;
            shadow_scene.nodes.push_back(volume);Model surfaces;
            check(compile_model(shadow_scene,surfaces,error)&&surfaces.segments.size()==1&&surfaces.segments[0].vertices.size()==6,
                "Static visible surfaces load without rasterizing shadow-volume nodes");
            check(shadow_scene.nodes[1].type==6&&shadow_scene.has_shadow_volumes,"Surface adapter leaves shadow source data unchanged");
            shadow_scene.nodes.erase(shadow_scene.nodes.begin());surfaces.source_path="preserve";
            check(!compile_model(shadow_scene,surfaces,error)&&surfaces.source_path=="preserve","Shadow-only model rejects atomically");
            shadow_scene=scene;shadow_scene.has_animation=true;
            check(!compile_model(shadow_scene,surfaces,error),"Static surface adapter still rejects animated models");
        }
        {
            auto damaged=scene;damaged.nodes[0].segments[0].normals.assign(4,{0,0,0});
            Model repaired;check(compile_model(damaged,repaired,error)&&repaired.derived_normal_vertices==6,
                "Zero source normals derive face normals for visible triangles");
            check(repaired.segments[0].vertices[0].normal==std::array<float,3>{0,0,1}&&
                damaged.nodes[0].segments[0].normals[0]==std::array<float,3>{0,0,0},"Normal repair leaves the authored source unchanged");
            damaged.nodes[0].segments[0].normals[0]={0,0,-1};
            check(compile_model(damaged,repaired,error)&&repaired.segments[0].vertices[0].normal[2]==-1,
                "Authored nonzero normals are preserved");
            damaged.nodes[0].segments[0].triangles.push_back({0,0,1});
            check(compile_model(damaged,repaired,error)&&repaired.degenerate_triangles==1&&repaired.segments[0].vertices.size()==6,
                "Degenerate source triangles are explicitly counted and skipped");
            damaged.nodes[0].segments[0].triangles={{0,0,1}};repaired.source_path="preserve";
            check(!compile_model(damaged,repaired,error)&&repaired.source_path=="preserve",
                "Entirely degenerate geometry rejects the model atomically");
        }
        {
            auto authored=model;authored.segments[0].vertices[0].uv={.125f,.875f};
            WorldGeometry world;world.add(authored,{2,-2,-2});
            std::vector<std::array<float,3>> positions;
            for(unsigned n:{0u,1u,2u,5u}){
                const auto p=authored.segments[0].vertices[n].position;
                positions.push_back({p[0]*2,p[1]*-2,p[2]*-2});
            }
            auto matched=world.match_strip(positions);
            check(matched&&matched->segments[0].vertices.size()==6,"Converted world triangle strip matches");
            check(matched->segments[0].vertices[0].uv==std::array<float,2>{.125f,.875f},"World bridge preserves authored UV orientation");
            const auto usage=world.take_stats();
            check(usage.matched_triangles==2&&usage.material_triangles.at("")==2,"World report identifies material triangle usage");
            check(world.take_stats().material_triangles.empty(),"World material counters reset between frames");
            positions[0][0]+=.001f;
            check(bool(world.match_strip(positions)),"World bridge tolerates guest float quantization");
            positions.back()[2]+=1;
            check(!world.match_strip(positions),"Partial world draw retains original atomically");
            positions.back()[2]-=1;
            auto conflicting=authored;conflicting.segments[0].vertices[0].uv={.5f,.5f};
            world.add(conflicting,{2,-2,-2});
            check(!world.match_strip(positions),"Ambiguous authored materials are rejected");
            WorldGeometry translated;translated.add(authored,{2,-2,-2},{10,20,30});
            positions[0][0]-=.001f;
            for(auto& p:positions){p[0]+=10;p[1]+=20;p[2]+=30;}
            auto placed=translated.match_strip(positions);
            check(placed&&placed->segments[0].vertices[0].uv==authored.segments[0].vertices[0].uv,
                "Translated converted world matches while preserving authored UVs");
            bool rejected=false;try{translated.add(authored,{2,-2,-2},{INFINITY,0,0});}catch(const std::exception&){rejected=true;}
            check(rejected,"Nonfinite world translation rejects before indexing");
            const auto source=authored.segments[0].vertices[0].position;auto guest=source;guest[0]+=.5f;
            WorldGeometry bound;bound.add(authored,{1,1,1},{},{{source,guest}});
            std::vector<std::array<float,3>> bound_strip;
            for(unsigned n:{0u,1u,2u,5u})bound_strip.push_back(authored.segments[0].vertices[n].position);
            check(bool(bound.match_strip(bound_strip)),"Explicit vertex binding retains exact original correspondence");
            bound_strip[0]=guest;auto bound_model=bound.match_strip(bound_strip);
            check(bound_model&&bound_model->segments[0].vertices[0].position==source&&
                bound_model->segments[0].vertices[0].uv==authored.segments[0].vertices[0].uv,
                "Bound guest geometry renders unchanged authored position and UV");
            bound_strip[0][1]+=.1f;check(!bound.match_strip(bound_strip),"Unknown displacement still rejects bound draw atomically");
            rejected=false;try{bound.add(authored,{1,1,1},{},{{source,guest},{source,guest}});}catch(const std::exception&){rejected=true;}
            check(rejected,"Duplicate vertex bindings reject before indexing");
            guest[0]=INFINITY;rejected=false;try{bound.add(authored,{1,1,1},{},{{source,guest}});}catch(const std::exception&){rejected=true;}
            check(rejected,"Nonfinite vertex binding rejects before indexing");
            guest=source;guest[0]+=.5f;auto seam=authored;seam.segments[0].vertices[0].uv={.5f,.5f};
            bound.add(seam,{1,1,1},{},{{source,guest}});bound_strip[0]=guest;
            check(!bound.match_strip(bound_strip),"Bound material UV seam remains ambiguous and rejects the draw");
        }
        scene.nodes[0].segments[0].colors={0xff123456,0xff112233,0xff445566,0xff778899};
        check(compile_model(scene,model,error)&&model.segments[0].vertices[0].has_color&&
            model.segments[0].vertices[0].color==0xff123456&&model.segments[0].vertices[5].color==0xff778899,
            "MSH vertex colors survive triangle expansion");
        scene.nodes[0].scale={2,3,4};scene.nodes[0].translation={10,20,30};
        check(compile_model(scene,model,error)&&std::abs(model.segments[0].vertices[0].position[0]-8.2f)<0.0001f,"Scale and translation");
        scene.has_cloth=true;check(!compile_model(scene,model,error),"Unsupported features rejected");
        psprecomp::GuestMemory memory;constexpr unsigned va=0x08801000,ia=0x08802000,record=0x08803004,table=0x08804000,fb=0x04000000;
        memory.aot_store32(record-4,123);memory.aot_store32(record,table);memory.aot_store32(record+4,va);memory.aot_store32(record+8,ia);
        memory.aot_store32(record+12,1);memory.aot_store32(record+16,3);memory.aot_store32(record+20,3);
        memory.aot_store32(table+4,1);memory.aot_store32(table+8,0);memory.aot_store32(table+12,0);
        for(unsigned i=0;i<3;++i)memory.aot_store16(ia+i*2,i);
        renegade::render_trace024::records[va]={"test",record,123,va,ia,3,3,32};
        constexpr unsigned prim=(4<<16)|3;
        check(bool(find_model_part(memory,va,ia,prim)),"Exact named part match");
        check(!find_model_part(memory,va,ia+2,prim),"Mismatched index rejected");
        memory.aot_store32(record+12,2);memory.aot_store32(record+16,6);memory.aot_store32(record+20,6);
        renegade::render_resources::records[va].vertex_count=6;renegade::render_resources::records[va].index_count=6;
        memory.aot_store32(table+20,1);memory.aot_store32(table+24,3);memory.aot_store32(table+28,3);
        auto second=renegade::render_resources::resolve_part(memory,va+96,ia+6,prim);
        check(second.resource&&second.slot==1,"Shared resolver identifies second render part exactly");
        renegade::render_resources::records[va+64]={"stale interior",record,999,va+64,ia,3,3,32};
        second=renegade::render_resources::resolve_part(memory,va+96,ia+6,prim);
        check(second.resource&&second.slot==1&&second.resource->name=="test",
              "Stale interior registration cannot hide a live model part");
        renegade::render_resources::records.erase(va+64);
        memory.aot_store32(table+20,0xffffffff);
        check(!renegade::render_resources::resolve_part(memory,va+96,ia+6,(4<<16)|1).resource,
              "Part length cannot wrap to a valid primitive count");
        memory.aot_store32(record+12,1);memory.aot_store32(record+16,3);memory.aot_store32(record+20,3);
        renegade::render_resources::records[va].vertex_count=3;renegade::render_resources::records[va].index_count=3;
        std::array<unsigned,256> c{};c[0x9d]=8;c[0xd2]=3;c[0xd5]=7|(7<<10);c[0x12]=0x11e3;c[0xde]=1;c[0x55]=0xffffff;c[0x58]=255;
        for(unsigned reg:{0x42,0x43,0x45,0x46})c[reg]=std::bit_cast<unsigned>(4.f)>>8;
        vcs::GeTransformState transform{};vcs::reset_ge_transform_state(transform);vcs::GeRenderStats stats;
        check(vcs::render_ge_primitive(memory,c,transform,va,ia,prim,stats,error),"Render MSH part");
        check(stats.triangles==2&&stats.pixels_written>0,"Replacement geometry rasterized");
        // Framebuffer alpha belongs to the PSP stencil path; verify RGB here.
        bool correct_color=false;for(unsigned i=0;i<64;++i)correct_color|=(memory.aot_load32(fb+i*4)&0xffffff)==0x563412;
        check(correct_color,"Classic BGRA color renders with correct RGB channels");
        check(stats.next_index_address==ia+6&&stats.next_vertex_address==va,"Original stream advancement preserved");
        check(memory.aot_load32(va)==0,"Original vertex memory preserved");
        auto textured_path=directory/"models/textured/part-0.msh";
        std::filesystem::create_directories(textured_path.parent_path());
        auto save=[&](const std::filesystem::path& path,const B& contents){std::ofstream f(path,std::ios::binary);f.write(reinterpret_cast<const char*>(contents.data()),contents.size());};
        save(textured_path,fixture("diffuse.tga"));
        Model textured;check(!load_model(textured_path,textured,error),"Missing diffuse rejects complete override");
        B tga(18);tga[2]=2;tga[12]=1;tga[14]=1;tga[16]=32;tga[17]=0x28;
        tga.insert(tga.end(),{0,255,0,255});save(textured_path.parent_path()/"diffuse.tga",tga);
        check(load_model(textured_path,textured,error)&&textured.segments[0].texture&&
              textured.segments[0].texture->rgba[1]==255,"MSH diffuse image loaded");
        auto binding_path=directory/"model.bindings";
        {std::ofstream f(binding_path);f<<"RS_SKIN_BINDINGS 1\n1\n1 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1\n";}
        SkinModel skin;
        check(load_skin(textured_path,binding_path,skin,error)&&skin.bind_model.segments[0].texture&&
              skin.bind_model.segments[0].texture->rgba[1]==255&&skin.influences[0].size()==6,
              "Skin loader combines mapping geometry and diffuse image");
        save(textured_path,fixture("missing.tga"));
        check(!load_skin(textured_path,binding_path,skin,error)&&skin.bind_model.segments[0].texture->rgba[1]==255,
              "Skin load with missing material preserves previous complete output");
        save(textured_path,fixture("../diffuse.tga"));
        check(!load_model(textured_path,textured,error)&&textured.segments[0].texture->rgba[1]==255,
              "Unsafe reference rejected and previous output preserved");
        save(textured_path,fixture("diffuse.tga"));
        renegade::render_trace024::records[va].name="textured";
        for(unsigned i=0;i<64;++i)memory.aot_store32(fb+i*4,0);
        vcs::GeRenderStats textured_stats;
        check(vcs::render_ge_primitive(memory,c,transform,va,ia,prim,textured_stats,error),"Render own diffuse texture");
        bool green=false;for(unsigned i=0;i<64;++i)green|=(memory.aot_load32(fb+i*4)&0xffffff)==0x00ff00;
        check(green,"Model diffuse renders green even when original GE texturing is disabled");
        // A mesh's explicit material wins over a simultaneous global VRAM
        // texture replacement; it must never inherit the blue global image.
        B global_tga=tga;global_tga[18]=255;global_tga[19]=0;global_tga[20]=0;
        const auto original_id=texture_id(1,1,B{255,0,0,255});
        save(directory/"textures"/(original_id+".tga"),global_tga);
        check(find_texture(1,1,B{255,0,0,255})->rgba[2]==255,"Conflicting global replacement is active");
        constexpr unsigned original_texture=0x04010000;
        memory.aot_store32(original_texture,0xff0000ff);
        c[0x1e]=1;c[0xa0]=original_texture&0xffffff;c[0xa8]=0x040001;c[0xb8]=0;c[0xc3]=3;c[0xc9]=3;
        for(unsigned i=0;i<64;++i)memory.aot_store32(fb+i*4,0);
        check(vcs::render_ge_primitive(memory,c,transform,va,ia,prim,textured_stats,error),"Mesh/global conflict draw");
        green=false;bool blue=false;
        for(unsigned i=0;i<64;++i){auto rgb=memory.aot_load32(fb+i*4)&0xffffff;green|=rgb==0x00ff00;blue|=rgb==0xff0000;}
        check(green&&!blue,"Explicit mesh material takes priority over global VRAM replacement");
        c[0x1e]=0;
        const B png{137,80,78,71,13,10,26,10,0,0,0,13,73,72,68,82,0,0,0,1,0,0,0,2,8,6,0,0,0,153,129,182,39,0,0,0,18,73,68,65,84,120,156,99,248,207,192,208,192,192,240,159,225,63,0,15,253,3,126,249,223,138,13,0,0,0,0,73,69,78,68,174,66,96,130};
        std::filesystem::remove(textured_path.parent_path()/"diffuse.tga");
        save(textured_path.parent_path()/"diffuse.png",png);
        check(load_model(textured_path,textured,error)&&textured.segments[0].texture->height==2&&
              textured.segments[0].texture->rgba[3]==128,"PNG upgrades TGA reference and preserves alpha");
        B dds(128);dds[0]='D';dds[1]='D';dds[2]='S';dds[3]=' ';
        auto put=[&](unsigned at,unsigned value){for(unsigned i=0;i<4;++i)dds[at+i]=value>>(i*8);};
        put(4,124);put(8,0x100f);put(12,1);put(16,1);put(20,4);put(76,32);put(80,0x41);
        put(88,32);put(92,0xff);put(96,0xff00);put(100,0xff0000);put(104,0xff000000);put(108,0x1000);
        dds.insert(dds.end(),{0,0,255,255});save(textured_path.parent_path()/"diffuse.dds",dds);
        check(load_model(textured_path,textured,error)&&textured.segments[0].texture->rgba==B({0,0,255,255}),
              "DDS upgrade takes precedence over PNG");
        save(textured_path.parent_path()/"diffuse.dds",B{1,2,3});
        check(!load_model(textured_path,textured,error)&&textured.segments[0].texture->rgba==B({0,0,255,255}),
              "Broken preferred image rejects model atomically");
        auto material_draw=[&](const char* name,unsigned flags,unsigned color,unsigned background){
            auto path=directory/"models"/name/"part-0.msh";
            std::filesystem::create_directories(path.parent_path());save(path,fixture(nullptr,flags,color));
            renegade::render_trace024::records[va].name=name;
            for(unsigned i=0;i<64;++i)memory.aot_store32(fb+i*4,background);
            vcs::GeRenderStats result;
            check(vcs::render_ge_primitive(memory,c,transform,va,ia,prim,result,error),"Material draw succeeds");
            return result;
        };
        auto contains_rgb=[&](unsigned color){for(unsigned i=0;i<64;++i)if((memory.aot_load32(fb+i*4)&0xffffff)==color)return true;return false;};
        material_draw("blend",8|4,0x80123456,0x00ff0000);
        // round((86*128 + 255*127)/255) = 170 for blue.
        check(contains_rgb(0xaa1a09),"Source-alpha blend uses MSH flag");
        material_draw("add",8|64,0x80123456,0x00010203);
        check(contains_rgb(0x2c1c0c),"Additive material adds alpha-scaled color");
        auto cut=material_draw("cut",8|16,0x7f123456,0);
        check(cut.pixels_written==0,"Cutout rejects alpha below 128");
        auto edge=material_draw("edge",8|16,0x80123456,0);
        check(edge.pixels_written>0,"Cutout accepts alpha 128");
        c[0x17]=1; // hostile inherited lighting must not darken UNLIT material
        material_draw("unlit",8|1,0xff123456,0);
        check(contains_rgb(0x563412),"Unlit bypasses original lighting");
        material_draw("unlit-glow",8|1|2,0xff123456,0);
        check(contains_rgb(0x563412),"Authored unlit glow base pass is unaffected by hostile inherited lighting");
        material_draw("unlit-glow-transparent",8|1|2|4,0x80123456,0x00ff0000);
        check(contains_rgb(0xaa1a09),"Unlit glow base pass preserves authored source-alpha blend");c[0x17]=0;
        c[0x17]=1;material_draw("glow-emissive",8|2|32,0xff123456,0);
        check(contains_rgb(0x563412),"Glow surface uses authored emission independent of inherited lighting");c[0x17]=0;
        c[0x9b]=0;auto side0=material_draw("one-side",0,0xff123456,0);
        c[0x9b]=1;auto side1=material_draw("one-side",0,0xff123456,0);
        check((side0.pixels_written==0)!=(side1.pixels_written==0),"Single-sided material respects winding");
        auto both=material_draw("two-side",8,0xff123456,0);
        c[0x9b]=0;auto both_other=material_draw("two-side",8,0xff123456,0);
        check(both.pixels_written>0&&both_other.pixels_written>0,"Double-sided material survives either culling direction");
        auto original_commands=c;
        c[0x17]=1;c[0x18]=1;c[0x65]=std::bit_cast<unsigned>(1.f)>>8;
        c[0x5b]=std::bit_cast<unsigned>(16.f)>>8;c[0x91]=0xffffff;
        c[0x5c]=0xffffff;c[0x5d]=255;c[0x55]=0xffffff;c[0x58]=255;
        c[0x57]=0xffffff;c[0x5f]=1;
        auto gloss_draw=[&](const char* name,unsigned alpha,unsigned flags,unsigned type,std::array<float,3> tint,bool compressed_dds=false){
            auto path=directory/"models"/name/"part-0.msh";
            std::filesystem::create_directories(path.parent_path());save(path,fixture("mask.tga",flags,0xffffffff,type,tint));
            B image(18);image[2]=2;image[12]=1;image[14]=1;image[16]=32;image[17]=0x28;
            image.insert(image.end(),{0,0,0,static_cast<std::uint8_t>(compressed_dds?255:alpha)});save(path.parent_path()/"mask.tga",image);
            if(compressed_dds){
                B compressed(128);compressed[0]='D';compressed[1]='D';compressed[2]='S';compressed[3]=' ';
                auto set=[&](unsigned offset,unsigned value){for(unsigned k=0;k<4;++k)compressed[offset+k]=value>>(k*8);};
                set(4,124);set(8,0x81007);set(12,4);set(16,4);set(20,16);set(76,32);set(80,4);
                set(84,0x35545844);set(108,0x1000);
                compressed.insert(compressed.end(),{static_cast<std::uint8_t>(alpha),0,0,0,0,0,0,0,0,0,0,0,0,0,0,0});
                save(path.parent_path()/"mask.dds",compressed);
            }
            renegade::render_trace024::records[va].name=name;
            for(unsigned i=0;i<64;++i)memory.aot_store32(fb+i*4,0x00010203);
            vcs::GeRenderStats result;
            check(vcs::render_ge_primitive(memory,c,transform,va,ia,prim,result,error)&&result.triangles==2,
                  "Gloss model renders replacement geometry");return result;
        };
        auto black_mask=gloss_draw("gloss-black",0,8,4,{1,0,0});
        check(black_mask.pixels_written>0&&contains_rgb(0),"Zero gloss mask renders opaque black diffuse without highlight");
        gloss_draw("gloss-white",255,8,4,{1,0,0});
        check(contains_rgb(0x0000ff),"White gloss mask adds red highlight independently of black diffuse");
        gloss_draw("gloss-half",128,8,4,{1,0,0});
        check(contains_rgb(0x000080),"Half gloss mask scales highlight");
        gloss_draw("gloss-bc3-mask",128,8,4,{1,0,0},true);
        check(contains_rgb(0x000080),"BC3 DDS alpha reaches the model gloss renderer");
        gloss_draw("specular-flag",255,8|128,0,{0,1,0});
        check(contains_rgb(0x00ff00),"Normal material specular flag uses source highlight tint");
        gloss_draw("gloss-unlit",255,8|1,4,{1,0,0});
        check(contains_rgb(0),"Unlit gloss has no inherited highlights");
        auto gloss_cut=gloss_draw("gloss-cut",0,8|16,4,{1,0,0});
        check(gloss_cut.pixels_written==0,"Explicit gloss cutout still uses texture opacity");
        gloss_draw("gloss-blend",128,8|4,4,{1,0,0});
        check(contains_rgb(0x000142),"Gloss alpha masks highlight before explicit opacity blending");
        c[0x17]=0;gloss_draw("gloss-no-lighting",255,8,4,{1,0,0});
        check(contains_rgb(0),"Disabled game lighting produces no default white highlight");
        c[0x17]=1;c[0x91]=0;c[0x90]=0x0000ff;
        gloss_draw("gloss-diffuse-light",255,8,4,{1,1,1});
        check(contains_rgb(0x0000ff),"Diffuse-only incident light supplies red gloss highlight");
        c[0x91]=0x00ff00;
        gloss_draw("gloss-explicit-light",255,8,4,{1,1,1});
        check(contains_rgb(0x00ff00),"Explicit green specular light is not replaced by red diffuse");
        c[0x91]=0;c[0x18]=0;
        gloss_draw("gloss-disabled-light",255,8,4,{1,1,1});
        check(contains_rgb(0),"Disabled diffuse light cannot generate gloss");
        c[0x18]=1;
        gloss_draw("gloss-unlit-diffuse",255,8|1,4,{1,1,1});
        check(contains_rgb(0),"Unlit material ignores diffuse-derived gloss");
        MshScene invalid_gloss;Model preserved_gloss;preserved_gloss.source_path="preserve";
        check(parse_msh(fixture(nullptr,8,0xffffffff,4),invalid_gloss,error)&&
              !compile_model(invalid_gloss,preserved_gloss,error)&&preserved_gloss.source_path=="preserve",
              "Missing gloss mask rejects model atomically");
        check(parse_msh(fixture("mask.tga",8,0xffffffff,4,{2,0,0}),invalid_gloss,error)&&
              !compile_model(invalid_gloss,preserved_gloss,error)&&preserved_gloss.source_path=="preserve",
              "Unsupported specular tint rejects model atomically");
        c=original_commands;
        MshScene unsupported_scene;Model unchanged;
        check(parse_msh(fixture(nullptr,2),unsupported_scene,error)&&
              compile_model(unsupported_scene,unchanged,error)&&!unchanged.segments.empty(),
              "Glow surface metadata is retained by the material adapter");
        {
            c=original_commands;c[0x17]=1;c[0x18]=1;c[0x65]=std::bit_cast<unsigned>(1.f)>>8;
            c[0x5f]=0;c[0x90]=0xffffff;c[0x8f]=0;c[0x5c]=0;c[0x5d]=255;c[0x55]=0xffffff;c[0x56]=0xffffff;c[0x58]=255;
            auto normal_draw=[&](const char* name,B normal,unsigned type=27,unsigned diffuse_alpha=255){
                auto path=directory/"models"/name/"part-0.msh";std::filesystem::create_directories(path.parent_path());
                save(path,fixture("base.tga",8|32,0xffffffff,type,{1,0,0},"normal.tga"));
                auto base=tga;base[18]=base[19]=base[20]=255;base[21]=diffuse_alpha;save(path.parent_path()/"base.tga",base);
                save(path.parent_path()/"normal.tga",normal);
                renegade::render_trace024::records[va].name=name;
                for(unsigned i=0;i<64;++i)memory.aot_store32(fb+i*4,0);
                vcs::GeRenderStats result;check(vcs::render_ge_primitive(memory,c,transform,va,ia,prim,result,error),"Normalmapped draw succeeds");
                check(result.pixels_written>0,"Normalmapped geometry writes pixels");return path;
            };
            auto flat=tga;flat[18]=255;flat[19]=flat[20]=128;
            normal_draw("normal-flat",flat);check(contains_rgb(0xffffff),"Flat tangent normal receives full frontal diffuse lighting");
            auto side=flat;side[18]=128;side[20]=255;
            normal_draw("normal-side",side);
            unsigned brightest=0;for(unsigned i=0;i<64;++i)brightest=std::max(brightest,memory.aot_load32(fb+i*4)&255);
            check(brightest<=2,"Tangent normal changes per-pixel lighting without changing texture orientation");
            c[0x56]=0;c[0x91]=0xffffff;
            normal_draw("normal-gloss",flat,28,0);check(contains_rgb(0x0000ff),"Normal alpha controls gloss independently of diffuse alpha");
            flat[21]=0;normal_draw("normal-no-gloss",flat,28);check(contains_rgb(0),"Zero normal alpha suppresses gloss");
            auto path=normal_draw("normal-height",flat);
            {std::ofstream option(path.parent_path()/"normal.tga.option");option<<"-bump -format bump_alpha -bumpscale 10.0\n";}
            Model height;check(load_model(path,height,error)&&height.segments[0].normal_is_height&&height.segments[0].bump_scale==10,"Authored bump options are retained");
            std::filesystem::remove(path.parent_path()/"normal.tga");
            check(load_model(path,height,error)&&height.segments[0].normal_image_missing&&!height.segments[0].normal_texture,
                "Missing normal image is explicitly marked while authored diffuse remains usable");
            save(path.parent_path()/"normal.tga",B{1,2,3});height.source_path="retained";
            check(!load_model(path,height,error)&&height.source_path=="retained","Malformed present normal image rejects a whole model atomically");
            auto missing_path=directory/"models/missing-normal-gloss/part-0.msh";std::filesystem::create_directories(missing_path.parent_path());
            save(missing_path,fixture("base.tga",8|32,0xffffffff,28,{1,0,0},"missing.tga"));
            auto black=tga;black[18]=black[19]=black[20]=0;black[21]=255;save(missing_path.parent_path()/"base.tga",black);
            renegade::render_trace024::records[va].name="missing-normal-gloss";
            for(unsigned i=0;i<64;++i)memory.aot_store32(fb+i*4,0x00ff00);
            vcs::GeRenderStats missing_stats;check(vcs::render_ge_primitive(memory,c,transform,va,ia,prim,missing_stats,error),"Missing normal-mask diffuse fallback renders");
            check(missing_stats.pixels_written>0&&contains_rgb(0),"Missing authored normal gloss mask does not invent highlights from diffuse alpha");
            auto ramp_path=directory/"models/height-ramp/part-0.msh";std::filesystem::create_directories(ramp_path.parent_path());
            save(ramp_path,fixture("base.tga",8|32,0xffffffff,27,{1,1,1},"normal.tga"));
            auto base=tga;base[18]=base[19]=base[20]=255;save(ramp_path.parent_path()/"base.tga",base);
            B ramp(18);ramp[2]=2;ramp[12]=4;ramp[14]=1;ramp[16]=32;ramp[17]=0x28;
            for(unsigned value:{0u,32u,96u,192u})for(unsigned channel:{value,value,value,255u})ramp.push_back(channel);
            save(ramp_path.parent_path()/"normal.tga",ramp);
            {std::ofstream option(ramp_path.parent_path()/"normal.tga.option");option<<"-bump -bumpscale 10\n";}
            c[0x56]=0xffffff;renegade::render_trace024::records[va].name="height-ramp";
            for(unsigned i=0;i<64;++i)memory.aot_store32(fb+i*4,0);
            vcs::GeRenderStats ramp_stats;check(vcs::render_ge_primitive(memory,c,transform,va,ia,prim,ramp_stats,error),"Authored height map renders");
            unsigned minimum=255,maximum=0;for(unsigned i=0;i<64;++i){unsigned value=memory.aot_load32(fb+i*4)&255;if(value){minimum=std::min(minimum,value);maximum=std::max(maximum,value);}}
            check(maximum>minimum+10,"Height-map gradients change lighting across a flat surface");
            c=original_commands;
        }
        for(unsigned i=0;i<300;++i){
            renegade::render_trace024::records[va].name="absent-"+std::to_string(i);
            find_model_part(memory,va,ia,prim);
        }
        renegade::render_trace024::records[va].name="test";
        check(bool(find_model_part(memory,va,ia,prim)),"Negative cache saturation does not disable later overrides");
        memory.aot_store32(record-4,456);
        check(!find_model_part(memory,va,ia,prim),"Reused allocation identity rejected");
        vcs::GeRenderStats fallback;
        check(vcs::render_ge_primitive(memory,c,transform,va,ia,prim,fallback,error)&&fallback.triangles==1&&fallback.pixels_written==0,"Stale model falls back to original degenerate triangle");
        namespace resources=renegade::render_resources;
        resources::records.clear();
        auto resource=[&](unsigned i){
            resources::Record r{"resource-"+std::to_string(i),0x08880004+i*32,i+1,
                0x08900000+i*64,0x08a00000+i*8,1,1,32};
            memory.aot_store32(r.record-4,r.key);memory.aot_store32(r.record+4,r.vertices);
            memory.aot_store32(r.record+8,r.indices);memory.aot_store32(r.record+16,r.vertex_count);
            memory.aot_store32(r.record+20,r.index_count);memory.aot_store8(r.record+24,0);
            return r;
        };
        bool filled=true;for(unsigned i=0;i<resources::capacity;++i)filled&=resources::register_record(memory,resource(i));
        check(filled&&resources::records.size()==resources::capacity,"Registry accepts full live capacity");
        auto lookup=resource(0);
        check(resources::find_record(memory,lookup.record)&&resources::find_record(memory,lookup.record)->vertices==lookup.vertices,
              "Record address lookup validates and caches an existing resource");
        auto reused=resource(0);reused.name="new-model-at-reused-address";
        check(resources::register_record(memory,reused)&&resources::records.at(reused.vertices).name==reused.name,
              "Full registry still updates reused vertex addresses");
        auto extra=resource(resources::capacity);
        check(!resources::register_record(memory,extra)&&resources::records.size()==resources::capacity,
              "Full live registry remains bounded without evicting active resources");
        memory.aot_store32(reused.record-4,reused.key+9000);
        check(resources::register_record(memory,extra)&&resources::records.size()==resources::capacity&&
              !resources::records.contains(reused.vertices)&&resources::records.contains(extra.vertices),
              "Invalidated old allocation is reclaimed for a later resource");
        auto invalid=extra;invalid.key^=1;
        check(!resources::register_record(memory,invalid)&&resources::records.at(extra.vertices).key==extra.key,
              "Invalid incoming record cannot replace a live registration");
        memory.aot_store8(extra.record+24,1);
        check(!resources::is_live(memory,extra),"Changed compact vertex format invalidates identity");
        check(!resources::find_record(memory,extra.record),"Address cache rejects changed live identity");
        resources::records.clear();
        check(!resources::find_record(memory,lookup.record),"Address cache cannot retain erased record pointers");
        auto relocated=resource(0);relocated.vertices+=32;memory.aot_store32(relocated.record+4,relocated.vertices);
        check(resources::register_record(memory,relocated)&&resources::find_record(memory,relocated.record)->vertices==relocated.vertices,
              "Reused record address discovers relocated vertex storage");
        resources::records.clear();
        auto skin_directory=directory/"models/test-skin";
        std::filesystem::create_directories(skin_directory);
        save(skin_directory/"model.msh",fixture());
        std::filesystem::copy_file(binding_path,skin_directory/"model.bindings");
        auto cached_skin=find_skin_model("test-skin");
        check(bool(cached_skin)&&cached_skin==find_skin_model("test-skin"),"Whole skin candidate is cached");
        check(!find_skin_model("../test-skin")&&!find_skin_model("..")&&!find_skin_model("absent"),
              "Unsafe or missing skin names retain originals");
        std::filesystem::create_directories(directory/"models/incomplete-skin");
        save(directory/"models/incomplete-skin/model.msh",fixture());
        check(!find_skin_model("incomplete-skin"),"Missing binding file rejects whole skin candidate");
        for(unsigned i=0;i<300;++i)find_skin_model("absent-skin-"+std::to_string(i));
        check(bool(find_skin_model("test-skin"))&&cached_skin->bind_model.segments[0].vertices.size()==6,
              "Cache eviction preserves active ownership and later candidates");
        psprecomp::Runtime runtime;
        auto& rm=runtime.memory();
        rm.aot_store32(record-4,123);rm.aot_store32(record+4,va);rm.aot_store32(record+8,ia);
        rm.aot_store32(record+12,2);rm.aot_store32(record+16,3);rm.aot_store32(record+20,3);
        rm.aot_store8(record+24,0);rm.aot_store32(0x08bb1e5c,record);
        resources::records[va]={"test-skin",record,123,va,ia,3,3,32};
        PoseMatrix identity{1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
        constexpr unsigned matrix_address=0x08805000;
        for(unsigned i=0;i<16;++i){rm.aot_store32(0x08bb1e00+i*4,std::bit_cast<unsigned>(identity[i]));
            rm.aot_store32(matrix_address+i*4,std::bit_cast<unsigned>(identity[i]));}
        psprecomp::AllegrexContext context{};context.gpr[7]=matrix_address;
        runtime_pose_store.clear();diagnostic_pose_store.clear();
        for(unsigned i=0;i<300;++i){
            rm.aot_store32(matrix_address+48,std::bit_cast<unsigned>(float(i)));
            for(unsigned slot=0;slot<2;++slot){context.gpr[6]=slot;renegade::render_trace024::submission(runtime,context);}
        }
        PoseWorld final_world{1,0,0,0,1,0,0,0,1,299,0,0};
        auto captured=runtime_pose_store.match({record,123,va,ia,3,3},0,final_world);
        check(captured&&captured->bones.size()==2&&captured->bones[0][12]==299,
              "Production hook captures non-diagnostic resources beyond 256 calls without trace output");
        check(!diagnostic_pose_store.match({record,123,va,ia,3,3},0,final_world),
              "Runtime capture does not populate or depend on diagnostic store");
        auto draw_pose=std::make_shared<PoseSnapshot>(*captured);
        draw_pose->bones={identity,identity};draw_pose->worlds.assign(2,PoseWorld{1,0,0,0,1,0,0,0,1,0,0,0});
        constexpr unsigned command_pc=0x08806000;
        auto tag_batch=[&](){
            auto batch=command_pose_store.begin(draw_pose->identity,2);
            for(unsigned slot=0;slot<2;++slot){command_pose_store.expect(batch,slot,true);
                command_pose_store.record(batch,slot,command_pc+slot*4,0x04000000|prim,va,ia);}
            command_pose_store.complete(batch,draw_pose);
        };
        tag_batch();auto camera_transform=transform;camera_transform.world[9]=100;
        for(unsigned i=0;i<64;++i)rm.aot_store32(fb+i*4,0);
        vcs::GeRenderStats whole_stats;
        check(vcs::render_ge_primitive(rm,c,camera_transform,va,ia,prim,whole_stats,error,1,0,0,0,true,command_pc)&&
              whole_stats.triangles==2&&whole_stats.pixels_written>0,"Whole skin rasterizes once without double world transform");
        vcs::GeRenderStats suppressed;
        check(vcs::render_ge_primitive(rm,c,camera_transform,va,ia,prim,suppressed,error,1,0,0,0,true,command_pc+4)&&
              suppressed.triangles==0&&suppressed.pixels_written==0&&suppressed.next_index_address==ia+6,
              "Later original part suppressed with original stream advancement");
        tag_batch();vcs::GeRenderStats before_eviction,after_eviction;
        check(vcs::render_ge_primitive(rm,c,camera_transform,va,ia,prim,before_eviction,error,1,0,0,0,true,command_pc)&&
              before_eviction.triangles==2,"Replacement renders before pose eviction");
        for(unsigned i=0;i<128;++i)command_pose_store.begin(draw_pose->identity,2);
        check(vcs::render_ge_primitive(rm,c,camera_transform,va,ia,prim,after_eviction,error,1,0,0,0,true,command_pc+4)&&
              after_eviction.triangles==0&&after_eviction.pixels_written==0&&after_eviction.next_index_address==ia+6,
              "Evicted rendered pose retains validated suppression and stream advancement");
        // Two actors deliberately share resource, context, model and guest arrays.
        // Only their emitted commands and captured camera poses distinguish them.
        auto actor_left=std::make_shared<PoseSnapshot>(*draw_pose);
        auto actor_right=std::make_shared<PoseSnapshot>(*draw_pose);
        for(auto& w:actor_left->worlds){w[0]=w[4]=0.35f;w[9]=-0.5f;}
        for(auto& w:actor_right->worlds){w[0]=w[4]=0.35f;w[9]=0.5f;}
        auto queue_actor=[&](auto actor,unsigned pc){
            auto batch=command_pose_store.begin(actor->identity,2);
            for(unsigned slot=0;slot<2;++slot){command_pose_store.expect(batch,slot,true);
                command_pose_store.record(batch,slot,pc+slot*4,0x04000000|prim,va,ia);}
            check(command_pose_store.complete(batch,actor),"Independent actor pose completes");
            return batch;
        };
        command_pose_store.clear();
        queue_actor(actor_left,command_pc);queue_actor(actor_right,command_pc+16);
        auto actor_draw=[&](unsigned pc){
            for(unsigned i=0;i<64;++i)rm.aot_store32(fb+i*4,0);
            vcs::GeRenderStats result;
            check(vcs::render_ge_primitive(rm,c,camera_transform,va,ia,prim,result,error,1,0,0,0,true,pc),
                  "Interleaved actor draw succeeds");
            return result;
        };
        auto horizontal_bounds=[&](){std::array<int,2> bounds{8,-1};
            for(unsigned i=0;i<64;++i)if(rm.aot_load32(fb+i*4)&0xffffff){
                bounds[0]=std::min(bounds[0],int(i%8));bounds[1]=std::max(bounds[1],int(i%8));}
            return bounds;
        };
        auto left_draw=actor_draw(command_pc);auto left_bounds=horizontal_bounds();
        auto right_draw=actor_draw(command_pc+16);auto right_bounds=horizontal_bounds();
        check(left_draw.triangles==2&&right_draw.triangles==2&&left_draw.pixels_written>0&&right_draw.pixels_written>0&&
              left_bounds[1]<right_bounds[0],"Shared-resource actors render at distinct captured positions");
        auto left_tail=actor_draw(command_pc+4),right_tail=actor_draw(command_pc+20);
        check(left_tail.triangles==0&&right_tail.triangles==0&&left_tail.next_index_address==ia+6&&right_tail.next_index_address==ia+6,
              "Both actors independently suppress remaining original parts");
        // A bad second actor must not cancel the successful first actor's tail.
        auto bad_actor=std::make_shared<PoseSnapshot>(*actor_right);bad_actor->worlds[0][0]=0;
        queue_actor(actor_left,command_pc);queue_actor(bad_actor,command_pc+16);
        auto good_first=actor_draw(command_pc),bad_first=actor_draw(command_pc+16);
        auto good_tail=actor_draw(command_pc+4),bad_tail=actor_draw(command_pc+20);
        check(good_first.triangles==2&&good_tail.triangles==0&&bad_first.triangles==1&&bad_tail.triangles==1,
              "Failed actor retains originals without contaminating another actor's replacement decision");
        draw_pose=std::make_shared<PoseSnapshot>(*draw_pose);draw_pose->worlds[0][0]=0;tag_batch();
        vcs::GeRenderStats failed_first,failed_next;
        check(vcs::render_ge_primitive(rm,c,transform,va,ia,prim,failed_first,error,1,0,0,0,true,command_pc)&&
              vcs::render_ge_primitive(rm,c,transform,va,ia,prim,failed_next,error,1,0,0,0,true,command_pc+4)&&
              failed_first.triangles==1&&failed_next.triangles==1,"Failed deformation retains every original part");
        check(rm.aot_load32(va)==0,"Whole replacement does not modify original vertex storage");
        rm.aot_store32(record-4,999);context.gpr[6]=0;
        rm.aot_store32(matrix_address+48,std::bit_cast<unsigned>(400.f));
        renegade::render_trace024::submission(runtime,context);context.gpr[6]=1;
        renegade::render_trace024::submission(runtime,context);final_world[9]=400;
        check(!runtime_pose_store.match({record,123,va,ia,3,3},0,final_world),"Stale guest resource cannot capture a pose");
        runtime_pose_store.clear();resources::records.clear();
        std::filesystem::remove_all(directory);std::cout<<checks<<" model integration checks passed\n";return 0;
    }catch(const std::exception& e){std::cerr<<"After "<<checks<<" checks: "<<e.what()<<'\n';std::filesystem::remove_all(directory);return 1;}
}
