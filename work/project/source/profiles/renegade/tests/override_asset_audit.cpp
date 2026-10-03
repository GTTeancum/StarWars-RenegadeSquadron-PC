#include "../host/override_model.hpp"
#include "../host/override_skin.hpp"
#include "../host/override_store.hpp"
#include <fstream>
#include <iostream>
#include <iomanip>
#include <set>
#include <cmath>
#include <locale>
// Optional compatibility diagnostic. No proprietary asset is bundled or needed
// by the ordinary test suite. Input is a UTF-8 file with one local path per line.
int main(int argc,char** argv) {
    if(argc==3&&std::string(argv[1])=="--model-geometry") {
        using namespace renegade::overrides;
        MshScene scene;Model model;std::string error;
        if(!load_msh(std::filesystem::u8path(argv[2]),scene,error)||!compile_model(scene,model,error)){
            std::cerr<<error<<'\n';return 1;
        }
        std::cout<<std::setprecision(9)<<"[";bool first=true;
        for(const auto& segment:model.segments){
            if(!first)std::cout<<',';first=false;
            std::cout<<"{\"texture\":"<<std::quoted(segment.texture_name)<<",\"vertices\":[";
            bool first_vertex=true;for(const auto& v:segment.vertices){
                if(!first_vertex)std::cout<<',';first_vertex=false;
                std::cout<<'['<<v.position[0]<<','<<v.position[1]<<','<<v.position[2]<<','<<v.uv[0]<<','<<v.uv[1]<<']';
            }
            std::cout<<"]}";
        }
        std::cout<<"]\n";return 0;
    }
    if(argc==3&&(std::string(argv[1])=="--texture"||std::string(argv[1])=="--resolve-texture")) {
        using namespace renegade::overrides;
        Texture texture;std::string error;
        if(!load_texture(std::filesystem::u8path(argv[2]),texture,error)){
            std::cerr<<error<<'\n';return 1;
        }
        if(std::string(argv[1])=="--resolve-texture"){
            const auto replacement=find_texture(texture.width,texture.height,texture.rgba);
            std::cout<<"{\"original_id\":\""<<texture_id(texture.width,texture.height,texture.rgba)
                <<"\",\"matched\":"<<(replacement?"true":"false");
            if(replacement)std::cout<<",\"replacement_width\":"<<replacement->width
                <<",\"replacement_height\":"<<replacement->height<<",\"original_alpha\":"
                <<(replacement->use_original_alpha?"true":"false");
            std::cout<<"}\n";return replacement?0:3;
        }
        std::cout<<"{\"width\":"<<texture.width<<",\"height\":"<<texture.height
            <<",\"decoded_id\":\""<<texture_id(texture.width,texture.height,texture.rgba)<<"\"}\n";
        return 0;
    }
    if(argc==3&&std::string(argv[1])=="--materials") {
        renegade::overrides::MshScene scene;std::string error;
        if(!renegade::overrides::load_msh(std::filesystem::u8path(argv[2]),scene,error)){
            std::cerr<<error<<'\n';return 1;
        }
        std::cout<<std::setprecision(9)<<"[";
        bool first=true;for(const auto& m:scene.materials){
            if(!first)std::cout<<",";first=false;
            std::cout<<"{\"has_data\":"<<(m.has_data?"true":"false")
                <<",\"flags\":"<<unsigned(m.attributes[0])<<",\"render_type\":"<<unsigned(m.attributes[1])
                <<",\"specular\":["<<m.specular[0]<<","<<m.specular[1]<<","<<m.specular[2]<<","<<m.specular[3]
                <<"],\"stored_exponent\":"<<m.specular_exponent<<"}";
        }
        std::cout<<"]\n";return 0;
    }

    if(argc==6&&std::string(argv[1])=="--skin-rest-check") {
        using namespace renegade::overrides;
        SkinModel skin;Model output;std::string error;
        if(!load_skin(std::filesystem::u8path(argv[2]),std::filesystem::u8path(argv[3]),skin,error)){
            std::cerr<<error<<'\n';return 1;
        }
        std::ifstream input(std::filesystem::u8path(argv[4]));input.imbue(std::locale::classic());
        std::string magic;unsigned version=0,count=0;
        if(!(input>>magic>>version>>count)||magic!="RS_SKIN_POSE"||version!=1||!count||count>256)return 2;
        PoseSnapshot pose;pose.bones.resize(count);
        for(auto& m:pose.bones)for(auto& v:m)if(!(input>>v))return 2;
        input>>std::ws;if(!input.eof())return 2;
        double scale=0;try{std::size_t used=0;scale=std::stod(argv[5],&used);if(used!=std::string(argv[5]).size())return 2;}catch(...){return 2;}
        if(!std::isfinite(scale)||scale<=0)return 2;
        if(!deform_skin(skin,pose,output,error)){std::cerr<<error<<'\n';return 1;}
        double maximum=0;std::size_t vertices=0;
        for(std::size_t s=0;s<output.segments.size();++s)for(std::size_t i=0;i<output.segments[s].vertices.size();++i){
            ++vertices;for(unsigned k=0;k<3;++k){
                double expected=skin.bind_model.segments[s].vertices[i].position[k]*scale*(k==2?1:-1);
                maximum=std::max(maximum,std::abs(output.segments[s].vertices[i].position[k]-expected));
            }
        }
        std::cout<<"{\"vertices\":"<<vertices<<",\"bind_reconstruction_max_error\":"<<maximum<<"}\n";
        return maximum<1e-5?0:1;
    }
    if(argc==4&&std::string(argv[1])=="--skin-load") {
        using namespace renegade::overrides;
        SkinModel skin;Model deformed;std::string error;
        if(!load_skin(std::filesystem::u8path(argv[2]),std::filesystem::u8path(argv[3]),skin,error)){
            std::cerr<<error<<'\n';return 1;
        }
        PoseSnapshot pose;pose.bones.assign(PoseStore::max_bones,PoseMatrix{1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1});
        if(!deform_skin(skin,pose,deformed,error)){std::cerr<<error<<'\n';return 1;}
        std::size_t vertices=0,textured=0;for(const auto& s:deformed.segments){vertices+=s.vertices.size();textured+=bool(s.texture);}
        std::cout<<"{\"bindings\":"<<skin.bindings.size()<<",\"segments\":"<<deformed.segments.size()
                 <<",\"textured_segments\":"<<textured<<",\"vertices\":"<<vertices<<"}\n";
        return 0;
    }
    if(argc==3&&std::string(argv[1])=="--skin-identity") {
        using namespace renegade::overrides;
        MshScene scene;SkinModel skin;Model model;std::string error;
        if(!load_msh(std::filesystem::u8path(argv[2]),scene,error)){std::cerr<<error<<'\n';return 1;}
        PoseMatrix identity{1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
        PoseSnapshot pose;std::vector<SkinBinding> bindings;
        for(const auto& n:scene.nodes){bindings.push_back({n.index,static_cast<unsigned>(pose.bones.size()),identity});pose.bones.push_back(identity);}
        if(!compile_skin(scene,bindings,skin,error)||!deform_skin(skin,pose,model,error)){
            std::cerr<<error<<'\n';
            for(const auto& m:scene.materials)std::cerr<<m.name<<" flags="<<unsigned(m.attributes[0])<<" render_type="<<unsigned(m.attributes[1])<<'\n';
            return 1;
        }
        double maximum=0;std::size_t vertices=0;
        for(std::size_t s=0;s<model.segments.size();++s)for(std::size_t i=0;i<model.segments[s].vertices.size();++i){
            ++vertices;for(unsigned k=0;k<3;++k)maximum=std::max(maximum,double(std::abs(model.segments[s].vertices[i].position[k]-skin.bind_model.segments[s].vertices[i].position[k])));
        }
        for(auto& bone:pose.bones){bone[12]=2;bone[13]=3;bone[14]=4;}
        if(!deform_skin(skin,pose,model,error)){std::cerr<<error<<'\n';return 1;}
        double translated=0;
        for(std::size_t s=0;s<model.segments.size();++s)for(std::size_t i=0;i<model.segments[s].vertices.size();++i)
            for(unsigned k=0;k<3;++k)translated=std::max(translated,double(std::abs(model.segments[s].vertices[i].position[k]-skin.bind_model.segments[s].vertices[i].position[k]-float(k+2))));
        std::size_t weighted=0;for(const auto& n:scene.nodes)for(const auto& s:n.segments)weighted+=s.weights.size();
        std::cout<<"{\"vertices\":"<<vertices<<",\"source_weighted_vertices\":"<<weighted
            <<",\"identity_max_error\":"<<maximum<<",\"translation_max_error\":"<<translated<<"}\n";
        return maximum<1e-5&&translated<1e-5?0:1;
    }
    if(argc==3&&std::string(argv[1])=="--skeleton") {
        renegade::overrides::MshScene scene;std::string error;
        if(!renegade::overrides::load_msh(std::filesystem::u8path(argv[2]),scene,error)){
            std::cerr<<error<<'\n';return 1;
        }
        std::set<unsigned> bones;std::size_t weighted=0;
        for(const auto& n:scene.nodes)for(const auto& s:n.segments)for(const auto& weights:s.weights){
            ++weighted;for(auto w:weights)if(w.weight>0)bones.insert(n.envelope.empty()?w.bone:n.envelope[w.bone]);
        }
        std::cout<<"{\"weighted_vertices\":"<<weighted<<",\"nodes\":[";
        bool first=true;for(const auto& n:scene.nodes){
            if(!first)std::cout<<',';first=false;
            std::cout<<"{\"name\":"<<std::quoted(n.name)<<",\"parent\":"<<std::quoted(n.parent)
                <<",\"index\":"<<n.index<<",\"type\":"<<n.type<<",\"weighted\":"<<(bones.contains(n.index)?"true":"false");
            auto array=[](const char* name,const auto& a){std::cout<<",\""<<name<<"\":[";
                for(std::size_t i=0;i<a.size();++i){if(i)std::cout<<',';std::cout<<std::setprecision(9)<<a[i];}std::cout<<']';};
            array("translation",n.translation);array("rotation_xyzw",n.rotation);array("scale",n.scale);
            std::cout<<'}';
        }
        std::cout<<"]}\n";return 0;
    }
    if(argc==3&&std::string(argv[1])=="--model-load") {
        using namespace renegade::overrides;
        MshScene scene;Model model;std::string error;
        const auto path=std::filesystem::u8path(argv[2]);
        bool parsed=load_msh(path,scene,error);
        bool compiled=parsed&&compile_model(scene,model,error);
        bool loaded=compiled&&load_model_materials(path,model,error);
        std::size_t vertices=0,textured=0,missing_normals=0;for(const auto& segment:model.segments){vertices+=segment.vertices.size();textured+=bool(segment.texture);missing_normals+=segment.normal_image_missing;}
        std::cout<<"{\"parsed\":"<<(parsed?"true":"false")<<",\"compiled\":"<<(compiled?"true":"false")<<",\"loaded\":"<<(loaded?"true":"false")
                 <<",\"has_animation\":"<<(scene.has_animation?"true":"false")<<",\"has_cloth\":"<<(scene.has_cloth?"true":"false")
                 <<",\"has_shadow_volumes\":"<<(scene.has_shadow_volumes?"true":"false")
                 <<",\"vertices\":"<<vertices<<",\"textured_segments\":"<<textured<<",\"missing_normal_segments\":"<<missing_normals
                 <<",\"derived_normal_vertices\":"<<model.derived_normal_vertices<<",\"degenerate_triangles\":"<<model.degenerate_triangles
                 <<",\"error\":"<<std::quoted(error)<<",\"materials\":[";
        bool first=true;for(const auto& m:scene.materials){if(!first)std::cout<<',';first=false;
            std::cout<<"{\"name\":"<<std::quoted(m.name)<<",\"texture\":"<<std::quoted(m.textures[0])<<",\"textures\":[";
            for(unsigned slot=0;slot<4;++slot){if(slot)std::cout<<',';std::cout<<std::quoted(m.textures[slot]);}
            std::cout<<"],\"flags\":"<<unsigned(m.attributes[0])<<",\"render_type\":"<<unsigned(m.attributes[1])<<'}';}
        std::cout<<"]}\n";return loaded?0:1;
    }
    if(argc!=2){std::cerr<<"Usage: renegade_override_asset_audit path-list.txt\n";return 2;}
    std::ifstream list(argv[1]);if(!list)return 2;
    std::cout<<"path\tparsed\tcompiled\tnodes\ttriangles\ttextures\terror\n";
    std::string line;
    while(std::getline(list,line)) {
        if(!line.empty()&&line.back()=='\r')line.pop_back();if(line.empty())continue;
        renegade::overrides::MshScene scene;renegade::overrides::Model model;std::string error;
        bool parsed=renegade::overrides::load_msh(std::filesystem::u8path(line),scene,error);
        bool compiled=parsed&&renegade::overrides::compile_model(scene,model,error);
        std::size_t triangles=0;for(const auto& n:scene.nodes)for(const auto& s:n.segments)triangles+=s.triangles.size();
        std::cout<<line<<'\t'<<parsed<<'\t'<<compiled<<'\t'<<scene.nodes.size()<<'\t'<<triangles<<'\t';
        for(const auto& m:scene.materials)if(!m.textures[0].empty())std::cout<<m.textures[0]<<';';
        std::cout<<'\t'<<error<<'\n';
    }
}
