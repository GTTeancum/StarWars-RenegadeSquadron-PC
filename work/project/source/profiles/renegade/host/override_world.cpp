#include "override_world.hpp"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
namespace renegade::overrides {
namespace {
using Point=std::array<float,3>;
std::array<int,3> cell(const std::array<Point,3>& p){
    std::array<int,3> result{};
    for(unsigned k=0;k<3;++k){
        const double value=(double(p[0][k])+p[1][k]+p[2][k])/3/.05;
        if(!std::isfinite(value)||std::abs(value)>100000000)throw std::runtime_error("Invalid world coordinate");
        result[k]=int(std::floor(value));
    }
    return result;
}
float distance(const Point& a,const Point& b){float d=0;for(unsigned k=0;k<3;++k)d=std::max(d,std::abs(a[k]-b[k]));return d;}
bool degenerate(const std::array<Point,3>& p){
    Point a{},b{};for(unsigned k=0;k<3;++k){a[k]=p[1][k]-p[0][k];b[k]=p[2][k]-p[0][k];}
    const Point c{a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};
    return c[0]*c[0]+c[1]*c[1]+c[2]*c[2]<1e-12f;
}
}
void WorldGeometry::add(const Model& model,const Point& scale,const Point& translation,const std::vector<WorldVertexBinding>& bindings){
    for(auto value:scale)if(!std::isfinite(value)||std::abs(value)<1e-6f)throw std::runtime_error("Invalid world scale");
    for(auto value:translation)if(!std::isfinite(value))throw std::runtime_error("Invalid world translation");
    if(bindings.size()>4096)throw std::runtime_error("World vertex binding budget exceeded");
    for(std::size_t i=0;i<bindings.size();++i){
        const auto& b=bindings[i];
        for(unsigned k=0;k<3;++k)if(!std::isfinite(b.source[k])||!std::isfinite(b.guest[k]))throw std::runtime_error("Invalid world vertex binding");
        if(distance(b.source,b.guest)>32)throw std::runtime_error("World vertex binding displacement exceeded");
        for(std::size_t j=0;j<i;++j)if(distance(b.source,bindings[j].source)<.0001f)
            throw std::runtime_error("Duplicate world vertex binding");
    }
    for(const auto& segment:model.segments){
      auto material=segment;material.vertices.clear();material.vertices.shrink_to_fit();
      for(std::size_t i=0;i+2<segment.vertices.size();i+=3){
        Triangle t;t.material=material;
        std::array<Point,3> positions;
        for(unsigned n=0;n<3;++n){
            t.vertices[n]=segment.vertices[i+n];auto& v=t.vertices[n];
            float length=0;
            for(unsigned k=0;k<3;++k){v.position[k]=v.position[k]*scale[k]+translation[k];v.normal[k]/=scale[k];length+=v.normal[k]*v.normal[k];}
            if(!std::isfinite(length)||length<1e-12f)throw std::runtime_error("Invalid world normal");
            for(auto& value:v.normal)value/=std::sqrt(length);
            positions[n]=v.position;
        }
        t.match_positions=positions;
        if(!degenerate(positions))cells_[cell(positions)].push_back(t);
        bool changed=false;
        for(unsigned n=0;n<3;++n)for(const auto& b:bindings)if(distance(positions[n],b.source)<.0001f){t.match_positions[n]=b.guest;changed=true;break;}
        if(changed&&!degenerate(t.match_positions))cells_[cell(t.match_positions)].push_back(std::move(t));
      }
    }
}
std::shared_ptr<const Model> WorldGeometry::match_strip(const std::vector<Point>& strip) const {
    if(strip.size()<3||strip.size()>65535)return {};
    ++stats_.attempted_draws;
    auto result=std::make_shared<Model>();result->source_path="converted-world";
    for(std::size_t i=2;i<strip.size();++i){
        std::array<Point,3> p{strip[i-2],strip[i-1],strip[i]};if(i&1)std::swap(p[0],p[1]);
        if(degenerate(p))continue;
        const auto key=cell(p);const Triangle* found=nullptr;std::array<unsigned,3> mapping{};
        for(int x=-1;x<=1;++x)for(int y=-1;y<=1;++y)for(int z=-1;z<=1;++z){
            auto bucket=cells_.find({key[0]+x,key[1]+y,key[2]+z});if(bucket==cells_.end())continue;
            for(const auto& candidate:bucket->second){
                std::array<unsigned,3> order{0,1,2};
                do {
                    bool match=true;for(unsigned n=0;n<3;++n)match &= distance(p[n],candidate.match_positions[order[n]])<.003f;
                    if(!match)continue;
                    if(found){
                        if(found->material.texture_name!=candidate.material.texture_name||found->material.material_flags!=candidate.material.material_flags||
                           found->material.normal_texture_name!=candidate.material.normal_texture_name||found->material.per_pixel!=candidate.material.per_pixel||
                           found->material.normal_is_height!=candidate.material.normal_is_height||found->material.bump_scale!=candidate.material.bump_scale||
                           found->material.gloss!=candidate.material.gloss||found->material.specular!=candidate.material.specular||
                           found->material.specular_exponent!=candidate.material.specular_exponent){++stats_.ambiguous_draws;return {};}
                        for(unsigned n=0;n<3;++n)if(found->vertices[mapping[n]].uv!=candidate.vertices[order[n]].uv){++stats_.ambiguous_draws;return {};}
                    }
                    found=&candidate;mapping=order;break;
                }while(std::next_permutation(order.begin(),order.end()));
            }
        }
        if(!found)return {}; // Mixed/ambiguous draws retain the original intact.
        // Group adjacent triangles only: preserve translucent submission order.
        if(result->segments.empty()||result->segments.back().texture!=found->material.texture||
           result->segments.back().material_flags!=found->material.material_flags||
           result->segments.back().gloss!=found->material.gloss||result->segments.back().specular!=found->material.specular||
           result->segments.back().per_pixel!=found->material.per_pixel||result->segments.back().normal_texture!=found->material.normal_texture||
           result->segments.back().normal_is_height!=found->material.normal_is_height||result->segments.back().bump_scale!=found->material.bump_scale||
           result->segments.back().specular_exponent!=found->material.specular_exponent)
            result->segments.push_back(found->material);
        for(auto n:mapping)result->segments.back().vertices.push_back(found->vertices[n]);
    }
    if(result->segments.empty())return {};
    ++stats_.matched_draws;
    for(const auto& segment:result->segments){stats_.matched_triangles+=segment.vertices.size()/3;stats_.material_triangles[segment.texture_name]+=segment.vertices.size()/3;}
    return result;
}
const WorldGeometry* configured_world() noexcept {
    static const auto world=[]()->std::unique_ptr<WorldGeometry>{
        const char* manifest=std::getenv("RENEGADE_WORLD_GEOMETRY");if(!manifest||!*manifest)return {};
        try {
            std::ifstream input(manifest);std::string magic;unsigned version=0,count=0;Point scale{},translation{};
            if(!(input>>magic>>version>>scale[0]>>scale[1]>>scale[2])||magic!="RS_WORLD"||(version<1||version>3))
                throw std::runtime_error("Invalid world geometry manifest");
            if(version>=2&&!(input>>translation[0]>>translation[1]>>translation[2]))throw std::runtime_error("Missing world translation");
            if(!(input>>count)||!count||count>64)throw std::runtime_error("Invalid world model count");
            auto result=std::make_unique<WorldGeometry>();
            std::vector<Model> models(count);std::vector<std::vector<WorldVertexBinding>> bindings(count);
            for(unsigned i=0;i<count;++i){
                std::string name;if(!(input>>std::quoted(name)))throw std::runtime_error("Missing world model path");
                auto path=std::filesystem::path(manifest).parent_path()/std::filesystem::u8path(name);
                std::string error;if(!load_model(path,models[i],error))throw std::runtime_error(path.string()+": "+error);
            }
            if(version==3){
                unsigned size=0;if(!(input>>magic>>size)||magic!="RS_BINDINGS"||size>4096)throw std::runtime_error("Invalid world vertex bindings");
                for(unsigned i=0;i<size;++i){unsigned index=0;WorldVertexBinding b{};
                    if(!(input>>index>>b.source[0]>>b.source[1]>>b.source[2]>>b.guest[0]>>b.guest[1]>>b.guest[2])||index>=count)
                        throw std::runtime_error("Invalid world vertex binding entry");
                    bindings[index].push_back(b);
                }
            }
            for(unsigned i=0;i<count;++i)result->add(models[i],scale,translation,bindings[i]);
            input>>std::ws;if(!input.eof())throw std::runtime_error("Trailing world manifest data");
            std::cerr<<"[overrides] Converted world geometry loaded models="<<count<<"\n";return result;
        }catch(const std::exception& ex){std::cerr<<"[overrides] World geometry rejected: "<<ex.what()<<"\n";return {};}
    }();
    return world.get();
}
}
