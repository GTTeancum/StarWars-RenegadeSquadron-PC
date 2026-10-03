#include "override_store.hpp"
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <regex>
extern "C" {
#include <libavutil/sha.h>
#include <libavutil/mem.h>
}
namespace renegade::overrides {
namespace {
struct Store {
    std::filesystem::path root, dump;
    std::map<std::string,std::shared_ptr<const Texture>> cache;
    std::size_t bytes{};
    std::set<std::string> discovery_records;
    bool has_textures{};
    Store() {
        if(auto p=std::getenv("RENEGADE_OVERRIDE_ROOT");p&&*p)root=p;
        if(auto p=std::getenv("RENEGADE_DUMP_TEXTURES");p&&*p)dump=p;
        if(!root.empty())has_textures=std::filesystem::is_directory(root/"textures");
    }
};
Store& store(){static Store instance;return instance;}
void dump_tga(const std::filesystem::path& path,std::uint32_t w,std::uint32_t h,std::span<const std::uint8_t> rgba){
    std::filesystem::create_directories(path.parent_path());
    if(std::filesystem::exists(path))return;
    std::ofstream f(path,std::ios::binary);
    unsigned char header[18]{};header[2]=2;header[12]=w&255;header[13]=w>>8;
    header[14]=h&255;header[15]=h>>8;header[16]=32;header[17]=0x28;
    f.write(reinterpret_cast<char*>(header),18);
    for(std::size_t i=0;i<rgba.size();i+=4){char bgra[]{char(rgba[i+2]),char(rgba[i+1]),char(rgba[i]),char(rgba[i+3])};f.write(bgra,4);}
    if(!f)throw std::runtime_error("Cannot write texture discovery image");
}
}
bool textures_enabled() noexcept {try{return store().has_textures||!store().dump.empty();}catch(...){return false;}}
std::string texture_id(std::uint32_t w,std::uint32_t h,std::span<const std::uint8_t> rgba){
    if(!w||!h||w>4096||h>4096||rgba.size()!=std::size_t(w)*h*4)throw std::invalid_argument("Invalid texture identity dimensions");
    auto* sha=av_sha_alloc();if(!sha)throw std::bad_alloc();
    av_sha_init(sha,256);
    std::uint8_t dimensions[8];for(unsigned i=0;i<4;++i){dimensions[i]=w>>(8*i);dimensions[i+4]=h>>(8*i);}
    av_sha_update(sha,dimensions,8);av_sha_update(sha,rgba.data(),rgba.size());
    std::uint8_t digest[32];av_sha_final(sha,digest);av_free(sha);
    constexpr char hex[]="0123456789abcdef";std::string id="tex-v1-";
    for(auto b:digest){id+=hex[b>>4];id+=hex[b&15];}return id;
}
std::shared_ptr<const Texture> find_texture(std::uint32_t w,std::uint32_t h,std::span<const std::uint8_t> rgba,
                                          const TextureSource* source) noexcept {
    try {
        auto& s=store();auto id=texture_id(w,h,rgba);
        // Capture every encountered source identity, including HUD sprites,
        // framebuffer textures and other resources with no model/name record.
        // Discovery failures must not disable a valid replacement.
        if(!s.dump.empty())try {
            std::ostringstream record;
            record<<"{\"id\":\""<<id<<"\",\"file\":\""<<id<<".tga\",\"width\":"<<w<<",\"height\":"<<h;
            if(source)record<<",\"address\":"<<source->address<<",\"format\":"<<source->format
                <<",\"buffer_width\":"<<source->buffer_width<<",\"mip_level\":"<<source->mip_level
                <<",\"clut_address\":"<<source->clut_address<<",\"swizzled\":"<<(source->swizzled?"true":"false");
            record<<"}";
            const auto line=record.str();
            if(!s.discovery_records.contains(line)){
                dump_tga(s.dump/(id+".tga"),w,h,rgba);
                std::ofstream manifest(s.dump/"textures.jsonl",std::ios::app);
                manifest<<line<<'\n';manifest.flush();
                if(!manifest)throw std::runtime_error("Cannot write texture discovery manifest");
                // Bounded deduplication; duplicates after eviction are harmless.
                if(s.discovery_records.size()>=16384)s.discovery_records.clear();
                s.discovery_records.insert(line);
            }
        }catch(const std::exception& ex){std::cerr<<"[overrides] discovery: "<<ex.what()<<'\n';}
        if(auto it=s.cache.find(id);it!=s.cache.end())return it->second;
        // Bounded positive and negative cache. Existing shared handles remain valid.
        if(s.cache.size()>=4096||s.bytes>=256u*1024u*1024u){s.cache.clear();s.bytes=0;}
        std::shared_ptr<Texture> replacement;
        if(!s.root.empty())for(auto extension:{".dds",".tga",".png"}){
            auto path=s.root/"textures"/(id+extension);
            if(!std::filesystem::is_regular_file(path))continue;
            auto candidate=std::make_shared<Texture>();std::string error;
            if(load_texture(path,*candidate,error)){replacement=std::move(candidate);break;}
            std::cerr<<"[overrides] "<<path.string()<<": "<<error<<"; retaining original or next candidate\n";
        }
        // Normal map for this texture, used by the per-pixel lighting. A normal
        // map without a colour replacement keeps the original pixels.
        std::shared_ptr<Texture> normal_map;
        if(!s.root.empty())for(auto extension:{".dds",".tga",".png"}){
            auto path=s.root/"textures"/(id+"_n"+extension);
            if(!std::filesystem::is_regular_file(path))continue;
            auto candidate=std::make_shared<Texture>();std::string error;
            if(load_texture(path,*candidate,error)){normal_map=std::move(candidate);break;}
            std::cerr<<"[overrides] "<<path.string()<<": "<<error<<"; normal map ignored\n";
        }
        if(normal_map && !replacement){
            replacement=std::make_shared<Texture>();
            replacement->width=w;replacement->height=h;replacement->rgba.assign(rgba.begin(),rgba.end());
        }
        if(replacement && normal_map){
            s.bytes+=normal_map->rgba.size();
            std::cerr<<"[overrides] normal map "<<id<<"_n loaded ("<<normal_map->width<<"x"<<normal_map->height<<")\n";
            replacement->normal_map=std::move(normal_map);
        }
        if(replacement){
            const auto policy=s.root/"textures"/(id+".json");
            if(std::filesystem::exists(policy)){
                // Fail closed once, just like a missing/invalid image candidate.
                s.cache.emplace(id,nullptr);
                if(std::filesystem::file_size(policy)>1024)throw std::runtime_error("Texture alpha policy exceeds 1024 bytes");
                std::ifstream input(policy);std::string text((std::istreambuf_iterator<char>(input)),{});
                static const std::regex schema(R"policy(^\s*\{\s*"alpha"\s*:\s*"(original|replacement)"\s*\}\s*$)policy");
                std::smatch match;
                if(!input || !std::regex_match(text,match,schema))
                    throw std::runtime_error("Invalid texture alpha policy: "+policy.string());
                replacement->use_original_alpha=match[1]=="original";
            }
            s.bytes+=replacement->rgba.size();std::cerr<<"[overrides] texture "<<id<<" loaded"
                <<(replacement->use_original_alpha?" alpha=original":"")<<"\n";
        }
        s.cache[id]=replacement;return replacement;
    }catch(const std::exception& ex){std::cerr<<"[overrides] "<<ex.what()<<"; original texture retained\n";return {};}
}
}
