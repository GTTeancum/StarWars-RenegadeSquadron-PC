#include "override_model.hpp"
#include "override_resource_registry.hpp"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <fstream>
#include <sstream>
#include <set>
#include <map>
#include <stdexcept>
namespace renegade::overrides {
namespace {
using V=std::array<float,3>;
V rotate(const std::array<float,4>& q,V p) {
    V t{2*(q[1]*p[2]-q[2]*p[1]),2*(q[2]*p[0]-q[0]*p[2]),2*(q[0]*p[1]-q[1]*p[0])};
    return {p[0]+q[3]*t[0]+q[1]*t[2]-q[2]*t[1],p[1]+q[3]*t[1]+q[2]*t[0]-q[0]*t[2],p[2]+q[3]*t[2]+q[0]*t[1]-q[1]*t[0]};
}
void require(bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);}
}
bool compile_model(const MshScene& scene,Model& output,std::string& error){
    try {
        require(!scene.has_animation&&!scene.has_cloth,"Animated and cloth MSH features need a separate adapter");
        std::map<std::string,const MshNode*> names;
        for(const auto& n:scene.nodes)require(names.emplace(n.name,&n).second,"Duplicate model node");
        Model result;std::size_t total=0;
        for(const auto& node:scene.nodes){
            // Static visible surfaces are independent of optional volume payloads.
            // Existing game shadow submissions remain separate; never draw a volume as a surface.
            if(node.flags||node.type==6)continue;
            for(const auto& source:node.segments){
                require(source.weights.empty(),"Skinned MSH requires bone mapping");
                if(source.triangles.empty())continue;
                require(source.material<scene.materials.size(),"Invalid material");
                const auto& mat=scene.materials[source.material];
                const auto render_type=mat.attributes[1];
                require(render_type==0||render_type==4||render_type==27||render_type==28,"Unsupported MSH material render type");
                require(mat.textures[2].empty()&&mat.textures[3].empty(),"MSH detail/environment maps need a shader adapter");
                // Authored UNLIT+GLOW surfaces have a supported unlit base pass.
                // Preserve GLOW metadata; a screen-space bloom halo is not yet rendered.
                total+=source.triangles.size()*3;require(total<=1000000,"Override triangle budget exceeded");
                ModelSegment segment;
                segment.texture_name=mat.textures[0];
                segment.material_flags=mat.attributes[0];
                segment.per_pixel=(mat.attributes[0]&32)||render_type==27||render_type==28;
                if(render_type==27||render_type==28){
                    require(!mat.textures[1].empty(),"Normalmapped MSH requires a normal/bump image");
                    segment.normal_texture_name=mat.textures[1];
                }else require(mat.textures[1].empty(),"Unexpected MSH secondary image");
                segment.gloss=render_type==4||render_type==28||(mat.attributes[0]&128);
                require(std::isfinite(mat.specular_exponent)&&mat.specular_exponent>=0&&mat.specular_exponent<=1024,"Unsupported MSH specular exponent");
                segment.specular_exponent=mat.specular_exponent;
                if(segment.gloss){
                    require(!mat.textures[0].empty(),"Gloss MSH requires a diffuse alpha mask");
                    for(unsigned i=0;i<3;++i){require(std::isfinite(mat.specular[i])&&mat.specular[i]>=0&&mat.specular[i]<=1,
                        "Unsupported MSH specular color range");segment.specular[i]=mat.specular[i];}
                }
                for(auto tri:source.triangles){
                  for(auto index:tri)require(index<source.positions.size(),"Invalid vertex index");
                  const auto& a=source.positions[tri[0]];const auto& b=source.positions[tri[1]];const auto& c=source.positions[tri[2]];
                  V e1{},e2{};for(unsigned k=0;k<3;++k){e1[k]=b[k]-a[k];e2[k]=c[k]-a[k];}
                  V face{e1[1]*e2[2]-e1[2]*e2[1],e1[2]*e2[0]-e1[0]*e2[2],e1[0]*e2[1]-e1[1]*e2[0]};
                  float face_length=0;for(auto value:face)face_length+=value*value;
                  require(std::isfinite(face_length),"Invalid triangle geometry");
                  if(face_length<=1e-20f){++result.degenerate_triangles;continue;}
                  for(auto index:tri){
                    require(index<source.positions.size(),"Invalid vertex index");
                    ModelVertex vertex{source.positions[index],{0,0,1},{0,0}};
                    if(!source.colors.empty()){
                        require(index<source.colors.size(),"Invalid color count");
                        vertex.color=source.colors[index];vertex.has_color=true;
                    }
                    if(!source.normals.empty()){
                        require(index<source.normals.size(),"Invalid normal count");vertex.normal=source.normals[index];
                        float length=0;for(auto value:vertex.normal)length+=value*value;
                        require(std::isfinite(length),"Invalid source normal");
                        if(length<=1e-16f){vertex.normal=face;++result.derived_normal_vertices;}
                    }
                    if(!source.uv.empty()){require(index<source.uv.size(),"Invalid UV count");vertex.uv=source.uv[index];}
                    const MshNode* current=&node;std::size_t depth=0;
                    while(current){
                        require(++depth<=scene.nodes.size(),"Cyclic model hierarchy");
                        for(unsigned i=0;i<3;++i){require(std::abs(current->scale[i])>1e-8f,"Singular model scale");vertex.position[i]*=current->scale[i];vertex.normal[i]/=current->scale[i];}
                        vertex.position=rotate(current->rotation,vertex.position);vertex.normal=rotate(current->rotation,vertex.normal);
                        for(unsigned i=0;i<3;++i)vertex.position[i]+=current->translation[i];
                        if(current->parent.empty())current=nullptr;
                        else {auto it=names.find(current->parent);require(it!=names.end(),"Missing model parent");current=it->second;}
                    }
                    float length=0;for(auto v:vertex.normal)length+=v*v;
                    require(std::isfinite(length)&&length>1e-16f,"Invalid transformed normal");
                    for(auto& v:vertex.normal)v/=std::sqrt(length);
                    for(auto v:vertex.position)require(std::isfinite(v),"Invalid transformed position");
                    segment.vertices.push_back(vertex);
                  }
                }
                if(!segment.vertices.empty())result.segments.push_back(std::move(segment));
            }
        }
        require(!result.segments.empty(),"No visible MSH triangles");output=std::move(result);error.clear();return true;
    }catch(const std::exception& ex){error=ex.what();return false;}
}
bool load_model(const std::filesystem::path& path,Model& output,std::string& error){
    MshScene scene;Model candidate;
    if(!load_msh(path,scene,error)||!compile_model(scene,candidate,error)||
       !load_model_materials(path,candidate,error))return false;
    if(scene.has_shadow_volumes)std::cerr<<"[overrides] Static visible surfaces loaded; supplied shadow-volume payload not rendered: "<<path.string()<<"\n";
    output=std::move(candidate);return true;
}
bool load_model_materials(const std::filesystem::path& path,Model& output,std::string& error){
    try {
        Model candidate=output;
        candidate.source_path=path.string();
        std::map<std::filesystem::path,std::shared_ptr<Texture>> images;
        std::set<std::string> warned_missing;
        std::size_t image_bytes=0;
        auto image_for=[&](const std::string& name,bool required=true)->std::shared_ptr<Texture>{
            if(name.empty())return {};
            require(name!="."&&name!=".."&&name.find_first_of("/\\:")==std::string::npos,
                    "MSH diffuse texture must be a filename beside the model");
            auto relative=std::filesystem::u8path(name);
            auto texture_path=path.parent_path()/relative;
            // An upgraded DDS/PNG can replace an original TGA reference.
            bool found=false;
            for(const char* extension:{".dds",".tga",".png"}){
                auto alternative=texture_path;alternative.replace_extension(extension);
                if(std::filesystem::is_regular_file(alternative)){texture_path=alternative;found=true;break;}
            }
            if(!found){
                if(required)throw std::runtime_error("Missing MSH diffuse texture: "+name);
                if(warned_missing.insert(name).second)std::cerr<<"[overrides] Missing authored normal/bump image "<<name
                    <<"; geometric normals used for "<<path.string()<<"\n";
                return {};
            }
            auto& image=images[texture_path];
            if(!image){
                image=std::make_shared<Texture>();
                if(!load_texture(texture_path,*image,error))throw std::runtime_error(error);
                image_bytes+=image->rgba.size();
                require(image_bytes<=128u*1024u*1024u,"Model material texture budget exceeded");
            }
            return image;
        };
        for(auto& segment:candidate.segments){
            segment.texture=image_for(segment.texture_name);
            segment.normal_texture=image_for(segment.normal_texture_name,false);
            segment.normal_image_missing=!segment.normal_texture_name.empty()&&!segment.normal_texture;
            if(segment.normal_texture){
                auto option=path.parent_path()/std::filesystem::u8path(segment.normal_texture_name);option+=".option";
                std::ifstream input(option);std::string token;
                while(input>>token){
                    if(token=="-bump"||token=="-bumpmap")segment.normal_is_height=true;
                    if(token=="-bumpscale"){
                        require(bool(input>>segment.bump_scale)&&std::isfinite(segment.bump_scale)&&segment.bump_scale>0&&segment.bump_scale<=1024,"Invalid MSH bump scale");
                    }
                }
            }
        }
        if(candidate.derived_normal_vertices||candidate.degenerate_triangles)
            std::cerr<<"[overrides] Geometry repair derived_normals="<<candidate.derived_normal_vertices
                <<" degenerate_triangles="<<candidate.degenerate_triangles<<" model="<<path.string()<<"\n";
        output=std::move(candidate);error.clear();return true;
    }catch(const std::exception& ex){error=ex.what();return false;}
}
std::shared_ptr<const Model> find_model_part(const psprecomp::GuestMemory& memory,
    std::uint32_t va,std::uint32_t ia,std::uint32_t primitive) noexcept {
    static const char* root=std::getenv("RENEGADE_OVERRIDE_ROOT");
    if(!root||!*root||(primitive>>16)!=4)return {};
    try {
        const auto match=render_resources::resolve_part(memory,va,ia,primitive);
        if(!match.resource)return {};
        const auto& r=*match.resource;const auto part=match.slot;
        if(r.name.empty()||r.name=="."||r.name==".."||r.name.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.#")!=std::string::npos)return {};
        auto path=std::filesystem::path(root)/"models"/r.name/("part-"+std::to_string(part)+".msh");
        static std::map<std::filesystem::path,std::shared_ptr<Model>> cache;
        static std::size_t cached_bytes=0;
        if(auto found=cache.find(path);found!=cache.end())return found->second;
        // A bounded negative cache must not disable all later resource names.
        // A level can encounter more than 256 different parts before the target.
        if(cache.size()>=256){cache.clear();cached_bytes=0;}
        std::shared_ptr<Model> model;
        if(std::filesystem::is_regular_file(path)){
            std::string error;auto candidate=std::make_shared<Model>();
            if(load_model(path,*candidate,error)){
                std::size_t bytes=0;for(const auto& segment:candidate->segments){
                    bytes+=segment.vertices.size()*sizeof(ModelVertex);
                    if(segment.texture)bytes+=segment.texture->rgba.size();
                    if(segment.normal_texture)bytes+=segment.normal_texture->rgba.size();
                }
                require(bytes<=256u*1024u*1024u-cached_bytes,"Model override cache budget exceeded");
                cached_bytes+=bytes;model=std::move(candidate);std::cerr<<"[overrides] MSH part loaded "<<path.string()<<"\n";
            }else std::cerr<<"[overrides] "<<path.string()<<": "<<error<<"; original model retained\n";
        }
        cache.emplace(path,model);return model;
    }catch(...){return {};}
}
}
