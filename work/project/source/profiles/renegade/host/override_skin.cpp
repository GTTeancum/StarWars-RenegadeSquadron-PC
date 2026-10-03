#include "override_skin.hpp"
#include <cmath>
#include <map>
#include <stdexcept>
#include <fstream>
#include <sstream>
#include <locale>
#include <charconv>
#include <set>
#include <cstdlib>
#include <iostream>
#include <mutex>

namespace renegade::overrides {
namespace {
using V=std::array<float,3>;
void require(bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);}
V cross(V a,V b){return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
struct Transform {PoseMatrix matrix;std::array<V,3> normal;};
Transform transform(PoseMatrix m){
    for(float v:m)require(std::isfinite(v),"Nonfinite skin matrix");
    require(std::abs(m[3])<1e-5f&&std::abs(m[7])<1e-5f&&std::abs(m[11])<1e-5f&&std::abs(m[15]-1)<1e-5f,
            "Skin matrix must be affine");
    V a{m[0],m[1],m[2]},b{m[4],m[5],m[6]},c{m[8],m[9],m[10]};
    auto bc=cross(b,c);float det=a[0]*bc[0]+a[1]*bc[1]+a[2]*bc[2];
    require(std::isfinite(det)&&std::abs(det)>1e-12f,"Singular skin matrix");
    Transform t{m,{bc,cross(c,a),cross(a,b)}};
    for(auto& col:t.normal)for(auto& v:col){v/=det;require(std::isfinite(v),"Invalid skin normal matrix");}
    return t;
}
PoseMatrix multiply(const PoseMatrix& a,const PoseMatrix& b){
    PoseMatrix out{};for(unsigned j=0;j<4;++j)for(unsigned i=0;i<4;++i)
        for(unsigned k=0;k<4;++k)out[j*4+i]+=a[k*4+i]*b[j*4+k];
    return out;
}
}
bool load_skin_bindings(const std::filesystem::path& path,std::vector<SkinBinding>& output,std::string& error){
    try {
        // Read at most one bounded buffer, including for files changing size.
        constexpr std::size_t limit=1024*1024;
        std::ifstream file(path,std::ios::binary);
        require(bool(file),"Cannot open skin bindings");
        std::string data(limit+1,'\0');file.read(data.data(),data.size());
        require(!file.bad(),"Cannot read skin bindings");
        auto size=static_cast<std::size_t>(file.gcount());
        require(size<=limit,"Skin binding file exceeds limit");data.resize(size);
        std::istringstream input(data);input.imbue(std::locale::classic());
        auto number=[&](){
            std::string token;require(bool(input>>token),"Missing skin binding integer");
            std::uint32_t value{};
            auto parsed=std::from_chars(token.data(),token.data()+token.size(),value);
            require(parsed.ec==std::errc{}&&parsed.ptr==token.data()+token.size(),"Invalid skin binding integer");
            return value;
        };
        std::string magic;require(bool(input>>magic)&&magic=="RS_SKIN_BINDINGS","Invalid skin binding header");
        require(number()==1,"Unsupported skin binding version");
        auto count=number();require(count>0&&count<=4096,"Invalid skin binding count");
        std::vector<SkinBinding> candidate;candidate.reserve(count);std::set<std::uint32_t> indices;
        for(std::uint32_t i=0;i<count;++i){
            SkinBinding binding;binding.msh_index=number();binding.pose_slot=number();
            require(binding.pose_slot<PoseStore::max_bones,"Skin pose slot exceeds limit");
            require(indices.insert(binding.msh_index).second,"Duplicate skin bone binding");
            for(auto& v:binding.model_to_bone)require(bool(input>>v),"Invalid skin binding matrix");
            (void)transform(binding.model_to_bone);candidate.push_back(binding);
        }
        input>>std::ws;require(input.eof(),"Trailing skin binding data");
        output=std::move(candidate);error.clear();return true;
    }catch(const std::exception& e){error=e.what();return false;}
}
bool load_skin(const std::filesystem::path& msh,const std::filesystem::path& bindings,
               SkinModel& output,std::string& error){
    MshScene scene;std::vector<SkinBinding> mapping;SkinModel candidate;
    if(!load_skin_bindings(bindings,mapping,error)||!load_msh(msh,scene,error)||
       !compile_skin(scene,mapping,candidate,error)||
       !load_model_materials(msh,candidate.bind_model,error))return false;
    output=std::move(candidate);return true;
}
bool compile_skin(const MshScene& scene,std::span<const SkinBinding> bindings,SkinModel& output,std::string& error){
    try {
        require(!bindings.empty()&&bindings.size()<=4096,"Invalid skin binding count");
        SkinModel result;result.bindings.assign(bindings.begin(),bindings.end());
        std::map<unsigned,unsigned> lookup;
        for(unsigned i=0;i<bindings.size();++i){
            const auto& b=bindings[i];require(b.pose_slot<PoseStore::max_bones,"Skin pose slot exceeds limit");
            require(lookup.emplace(b.msh_index,i).second,"Duplicate skin bone binding");
            (void)transform(b.model_to_bone);
        }
        // Reuse the rigid compiler's hierarchy/material/vertex conversion. The
        // original scene remains intact for resolving its skin influences.
        // This adapter is driven exclusively by PoseSnapshot. Embedded ANM2
        // clips are not played; cloth and shadow-volume restrictions still apply.
        auto rigid=scene;rigid.has_animation=false;
        for(auto& n:rigid.nodes)for(auto& s:n.segments)s.weights.clear();
        if(!compile_model(rigid,result.bind_model,error))return false;
        for(const auto& n:scene.nodes){
            if(n.flags)continue;
            for(const auto& s:n.segments){
                if(s.triangles.empty())continue;
                require(s.weights.empty()||s.weights.size()==s.positions.size(),"Invalid skin weight count");
                std::vector<std::array<SkinInfluence,4>> vertices;
                for(auto tri:s.triangles)for(auto index:tri){
                    std::array<SkinInfluence,4> resolved{};
                    if(s.weights.empty()){
                        auto it=lookup.find(n.index);require(it!=lookup.end(),"Unweighted mesh node needs explicit binding");
                        resolved[0]={it->second,1};
                    }else{
                        float sum=0;
                        for(unsigned k=0;k<4;++k){auto w=s.weights[index][k];
                            require(std::isfinite(w.weight)&&w.weight>=0,"Invalid skin weight");
                            if(w.weight==0)continue;
                            auto bone=w.bone;
                            if(!n.envelope.empty()){require(bone<n.envelope.size(),"Invalid skin envelope index");bone=n.envelope[bone];}
                            auto it=lookup.find(bone);require(it!=lookup.end(),"Missing positive-weight bone binding");
                            resolved[k]={it->second,w.weight};sum+=w.weight;
                        }
                        require(std::isfinite(sum)&&sum>1e-8f,"Skin vertex has no usable weights");
                        for(auto& w:resolved)w.weight/=sum;
                    }
                    vertices.push_back(resolved);
                }
                result.influences.push_back(std::move(vertices));
            }
        }
        require(result.influences.size()==result.bind_model.segments.size(),"Skin segment mismatch");
        output=std::move(result);error.clear();return true;
    }catch(const std::exception& e){error=e.what();return false;}
}
std::shared_ptr<const SkinModel> find_skin_model(const std::string& resource) noexcept {
    static const char* root=std::getenv("RENEGADE_OVERRIDE_ROOT");
    if(!root||!*root)return {};
    try {
        if(resource.empty()||resource=="."||resource==".."||
           resource.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.#")!=std::string::npos)return {};
        static std::mutex mutex;std::lock_guard lock(mutex);
        static std::map<std::string,std::shared_ptr<const SkinModel>> cache;
        static std::size_t bytes=0;
        if(auto found=cache.find(resource);found!=cache.end())return found->second;
        // Bound both positive and negative entries. Active immutable results
        // retain ownership if an entry is evicted while a frame is in flight.
        if(cache.size()>=256){cache.clear();bytes=0;}
        std::shared_ptr<const SkinModel> result;
        auto directory=std::filesystem::path(root)/"models"/resource;
        auto path=directory/"model.msh";
        if(std::filesystem::is_regular_file(path)){
            auto candidate=std::make_shared<SkinModel>();std::string error;
            if(load_skin(path,directory/"model.bindings",*candidate,error)){
                std::size_t size=candidate->bindings.size()*sizeof(SkinBinding);
                std::set<const Texture*> textures;
                for(const auto& s:candidate->bind_model.segments){
                    size+=s.vertices.size()*sizeof(ModelVertex);
                    if(s.texture&&textures.insert(s.texture.get()).second)size+=s.texture->rgba.size();
                    if(s.normal_texture&&textures.insert(s.normal_texture.get()).second)size+=s.normal_texture->rgba.size();
                }
                for(const auto& s:candidate->influences)size+=s.size()*sizeof(std::array<SkinInfluence,4>);
                constexpr std::size_t budget=256u*1024u*1024u;
                require(size<=budget,"Skin candidate exceeds cache budget");
                if(size>budget-bytes){cache.clear();bytes=0;}
                bytes+=size;result=std::move(candidate);
                std::cerr<<"[overrides] Skin candidate loaded "<<path.string()<<'\n';
            }else std::cerr<<"[overrides] "<<path.string()<<": "<<error<<"; original model retained\n";
        }
        cache.emplace(resource,result);return result;
    }catch(...){return {};}
}
bool deform_skin(const SkinModel& skin,const PoseSnapshot& pose,Model& output,std::string& error){
    try {
        require(skin.bindings.size()<=4096&&!skin.bindings.empty(),"Invalid skin binding count");
        std::vector<Transform> transforms;transforms.reserve(skin.bindings.size());
        for(const auto& b:skin.bindings){
            require(b.pose_slot<pose.bones.size(),"Missing captured pose bone");
            transforms.push_back(transform(multiply(pose.bones[b.pose_slot],b.model_to_bone)));
        }
        Model result=skin.bind_model;
        require(skin.influences.size()==result.segments.size(),"Skin segment mismatch");
        for(std::size_t s=0;s<result.segments.size();++s){auto& segment=result.segments[s];
            require(skin.influences[s].size()==segment.vertices.size(),"Skin vertex mismatch");
            for(std::size_t i=0;i<segment.vertices.size();++i){auto& v=segment.vertices[i];V p{},n{};float sum=0;
                for(auto w:skin.influences[s][i]){
                    require(std::isfinite(w.weight)&&w.weight>=0,"Invalid compiled skin weight");
                    if(w.weight==0)continue;
                    require(w.binding<transforms.size(),"Invalid compiled skin binding");
                    const auto& t=transforms[w.binding];sum+=w.weight;
                    for(unsigned axis=0;axis<3;++axis){
                        float point=t.matrix[12+axis],normal=0;
                        for(unsigned k=0;k<3;++k){point+=t.matrix[k*4+axis]*v.position[k];normal+=t.normal[k][axis]*v.normal[k];}
                        p[axis]+=point*w.weight;n[axis]+=normal*w.weight;
                    }
                }
                require(std::isfinite(sum)&&std::abs(sum-1)<1e-4f,"Compiled skin weights not normalized");
                float length=0;for(float x:n)length+=x*x;
                require(std::isfinite(length)&&length>1e-16f,"Degenerate skinned normal");
                for(unsigned k=0;k<3;++k){require(std::isfinite(p[k]),"Nonfinite skinned position");n[k]/=std::sqrt(length);}
                v.position=p;v.normal=n;
            }
        }
        output=std::move(result);error.clear();return true;
    }catch(const std::exception& e){error=e.what();return false;}
}
bool deform_skin_camera(const SkinModel& skin,const PoseSnapshot& pose,Model& output,std::string& error){
    if(pose.worlds.size()!=pose.bones.size()){error="Missing camera-composed pose matrices";return false;}
    PoseSnapshot camera_pose;camera_pose.bones.resize(pose.worlds.size());
    for(std::size_t b=0;b<pose.worlds.size();++b){
        auto& matrix=camera_pose.bones[b];matrix[15]=1;
        for(unsigned j=0;j<4;++j)for(unsigned i=0;i<3;++i)matrix[j*4+i]=pose.worlds[b][j*3+i];
    }
    return deform_skin(skin,camera_pose,output,error);
}
}
