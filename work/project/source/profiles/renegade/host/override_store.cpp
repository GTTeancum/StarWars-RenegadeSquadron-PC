#include "override_store.hpp"
#include "key_prompts.hpp"
#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <regex>
#include <unordered_map>
#include <vector>
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
    // Least-recently-used eviction: a full cache drops its oldest images only,
    // instead of clearing everything (which reloaded the whole pack from disk
    // and stuttered whenever an HD pack outgrew the old 256 MB limit).
    std::unordered_map<std::string,std::uint64_t> last_use;
    std::uint64_t tick{};
    static constexpr std::size_t kBudget=std::size_t(2048)*1024u*1024u, kMaxEntries=16384;
    std::set<std::string> discovery_records;
    bool has_textures{};
    // Name-based replacement (Asura identifies textures by their path): names.tsv,
    // generated from the disc by work\tools\pcmods\texture_dump.py, maps every
    // content ID (all mip sizes, every level's copy) to the texture's name and copy
    // number; manifest.json optionally points names at other image files.
    struct Named { std::string name; unsigned copy{}; };
    std::unordered_map<std::string,Named> names;
    std::unordered_map<std::string,std::string> manifest;
    std::unordered_map<std::string,std::shared_ptr<const Texture>> keyboard_cache;  // key-cap prompt textures
    bool resolving_base{};
    Store() {
        if(auto p=std::getenv("RENEGADE_OVERRIDE_ROOT");p&&*p)root=p;
        if(auto p=std::getenv("RENEGADE_DUMP_TEXTURES");p&&*p)dump=p;
        if(!root.empty())has_textures=std::filesystem::is_directory(root/"textures");
        if(has_textures)load_names();
    }
    void load_names() {
        if(std::ifstream in{root/"textures"/"names.tsv"}) {
            std::string line;
            while(std::getline(in,line)) {
                if(line.empty()||line[0]=='#')continue;
                if(!line.empty()&&line.back()=='\r')line.pop_back();
                const auto a=line.find('\t'),b=a==std::string::npos?a:line.find('\t',a+1);
                if(b==std::string::npos)continue;
                names[line.substr(0,a)]=Named{line.substr(a+1,b-a-1),static_cast<unsigned>(std::strtoul(line.c_str()+b+1,nullptr,10))};
            }
            std::cerr<<"[overrides] texture names: "<<names.size()<<" IDs\n";
        }
        if(std::ifstream in{root/"textures"/"manifest.json"}) {
            // Flat JSON object of "name": "file" pairs.
            const std::string text((std::istreambuf_iterator<char>(in)),{});
            static const std::regex pair(R"re("((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)")re");
            for(std::sregex_iterator it(text.begin(),text.end(),pair),end;it!=end;++it)manifest[(*it)[1].str()]=(*it)[2].str();
            std::cerr<<"[overrides] texture manifest: "<<manifest.size()<<" entries\n";
        }
    }
    // Replacement candidates for an ID, best first: the exact ID, then this copy of
    // the named texture (name~2), then the name itself; a manifest entry for either
    // name redirects it to another file. Paths have no extension unless the
    // manifest gave one.
    std::vector<std::filesystem::path> stems(const std::string& id,const std::string& index,const std::string& colour,bool& loose_match) const {
        std::vector<std::filesystem::path> out{root/"textures"/id};
        auto it=names.find(id);
        loose_match=false;
        if(it==names.end()&&!index.empty()){it=names.find(index);loose_match=it!=names.end();}
        if(it==names.end()&&!colour.empty()){it=names.find(colour);loose_match=it!=names.end();}
        if(it==names.end())return out;
        std::vector<std::string> keys;
        if(it->second.copy>1)keys.push_back(it->second.name+"~"+std::to_string(it->second.copy));
        keys.push_back(it->second.name);
        for(const auto& key:keys) {
            if(const auto m=manifest.find(key);m!=manifest.end())out.push_back(root/"textures"/m->second);
            out.push_back(root/"textures"/key);
        }
        return out;
    }
};
// Image file for a stem: the stem itself when it names a file, else stem+extension.
std::vector<std::filesystem::path> image_files(const std::filesystem::path& stem,const std::string& suffix) {
    std::vector<std::filesystem::path> out;
    if(stem.has_extension()) {
        auto bare=stem; bare.replace_extension();
        if(suffix.empty())out.push_back(stem);
        else for(auto extension:{".dds",".tga",".png"})out.push_back(bare.string()+suffix+extension);
        return out;
    }
    for(auto extension:{".dds",".tga",".png"})out.push_back(stem.string()+suffix+extension);
    return out;
}
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
// Palette-independent identity: the stored index pixels (texture_dump.py tex-idx-).
std::string index_id(std::uint32_t w,std::uint32_t h,const TextureSource& source){
    auto* sha=av_sha_alloc();if(!sha)throw std::bad_alloc();
    av_sha_init(sha,256);
    std::uint8_t header[16];
    const std::uint32_t fields[4]{w,h,source.format,source.swizzled?1u:0u};
    for(unsigned f=0;f<4;++f)for(unsigned i=0;i<4;++i)header[f*4+i]=static_cast<std::uint8_t>(fields[f]>>(8*i));
    av_sha_update(sha,header,16);av_sha_update(sha,source.indices,source.index_bytes);
    std::uint8_t digest[32];av_sha_final(sha,digest);av_free(sha);
    constexpr char hex[]="0123456789abcdef";std::string id="tex-idx-";
    for(auto b:digest){id+=hex[b>>4];id+=hex[b&15];}return id;
}
// Colour-only identity (alpha ignored), matching texture_dump.py's tex-rgb- IDs.
std::string colour_id(std::uint32_t w,std::uint32_t h,std::span<const std::uint8_t> rgba){
    auto* sha=av_sha_alloc();if(!sha)throw std::bad_alloc();
    av_sha_init(sha,256);
    std::uint8_t dimensions[8];for(unsigned i=0;i<4;++i){dimensions[i]=w>>(8*i);dimensions[i+4]=h>>(8*i);}
    av_sha_update(sha,dimensions,8);
    std::vector<std::uint8_t> rgb(std::size_t(w)*h*3);
    for(std::size_t i=0,j=0;i<rgba.size();i+=4,j+=3){rgb[j]=rgba[i];rgb[j+1]=rgba[i+1];rgb[j+2]=rgba[i+2];}
    av_sha_update(sha,rgb.data(),rgb.size());
    std::uint8_t digest[32];av_sha_final(sha,digest);av_free(sha);
    constexpr char hex[]="0123456789abcdef";std::string id="tex-rgb-";
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
        // Button prompts show key caps while the keyboard/mouse is in use.
        if(key_prompts::active()&&!s.resolving_base&&!s.root.empty()){
            const auto named=s.names.find(id);
            if(named!=s.names.end()&&(named->second.name=="pspbuttons"||named->second.name.rfind("button_",0)==0)){
                if(auto it=s.keyboard_cache.find(id);it!=s.keyboard_cache.end())return it->second;
                std::shared_ptr<const Texture> base;
                if(auto it=s.cache.find(id);it!=s.cache.end())base=it->second;
                else{
                    // Resolve the pad version first (this call fills s.cache).
                    struct Off{bool& f;~Off(){f=false;}};
                    s.resolving_base=true;Off off{s.resolving_base};
                    base=find_texture(w,h,rgba,source);
                }
                Texture original;
                if(!base){original.width=w;original.height=h;original.rgba.assign(rgba.begin(),rgba.end());}
                auto variant=key_prompts::keyboard_variant(named->second.name,base?*base:original,s.root.parent_path()/"data");
                if(variant){
                    variant->keyboard_variant=true;
                    std::cerr<<"[overrides] keyboard prompts for "<<named->second.name<<"\n";
                    std::shared_ptr<const Texture> shared=std::move(variant);
                    s.keyboard_cache[id]=shared;return shared;
                }
                // Font not loaded yet: show the pad version for now, retry later.
                return base;
            }
        }
        if(auto it=s.cache.find(id);it!=s.cache.end()){s.last_use[id]=++s.tick;return it->second;}
        // Bounded positive and negative cache. Existing shared handles remain valid.
        if(s.cache.size()>=Store::kMaxEntries||s.bytes>=Store::kBudget){
            const auto size_of=[](const std::shared_ptr<const Texture>& t)->std::size_t{
                return t?t->rgba.size()+(t->normal_map?t->normal_map->rgba.size():0):0;};
            std::vector<std::pair<std::uint64_t,std::string>> order;order.reserve(s.cache.size());
            for(const auto& [key,texture]:s.cache)order.emplace_back(s.last_use[key],key);
            std::sort(order.begin(),order.end());
            for(const auto& [used,key]:order){
                if(s.bytes<=Store::kBudget/4*3&&s.cache.size()<=Store::kMaxEntries/4*3)break;
                auto it=s.cache.find(key);
                s.bytes-=std::min(s.bytes,size_of(it->second));s.cache.erase(it);s.last_use.erase(key);
            }
        }
        std::shared_ptr<Texture> replacement;
        std::filesystem::path chosen;  // stem that supplied the colour image (its .json policy applies)
        // The colour-only ID is needed only when the exact ID has no name.
        bool colour_match=false;
        const bool unnamed=!s.names.empty()&&!s.names.contains(id);
        const std::string index=(unnamed&&source&&source->indices&&source->index_bytes)?index_id(w,h,*source):std::string();
        const std::string colour=(unnamed&&!s.names.contains(index))?colour_id(w,h,rgba):std::string();
        const auto stems=s.root.empty()?std::vector<std::filesystem::path>{}:s.stems(id,index,colour,colour_match);
        for(const auto& stem:stems){
            for(const auto& path:image_files(stem,"")){
                if(!std::filesystem::is_regular_file(path))continue;
                auto candidate=std::make_shared<Texture>();std::string error;
                if(load_texture(path,*candidate,error)){replacement=std::move(candidate);chosen=path;break;}
                std::cerr<<"[overrides] "<<path.string()<<": "<<error<<"; retaining original or next candidate\n";
            }
            if(replacement)break;
        }
        // Normal map for this texture, used by the per-pixel lighting. A normal
        // map without a colour replacement keeps the original pixels.
        std::shared_ptr<Texture> normal_map;
        for(const auto& stem:stems){
            for(const auto& path:image_files(stem,"_n")){
                if(!std::filesystem::is_regular_file(path))continue;
                auto candidate=std::make_shared<Texture>();std::string error;
                if(load_texture(path,*candidate,error)){normal_map=std::move(candidate);break;}
                std::cerr<<"[overrides] "<<path.string()<<": "<<error<<"; normal map ignored\n";
            }
            if(normal_map)break;
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
            auto policy=chosen.empty()?s.root/"textures"/(id+".json"):chosen;
            policy.replace_extension(".json");
            // Matched on the picture or colours only: the game recoloured this
            // texture's palette (unit skins), so keep the game's alpha unless a
            // policy file says otherwise.
            if(colour_match&&chosen.stem().string().rfind("tex-v1-",0)!=0)replacement->use_original_alpha=true;
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
                <<(chosen.empty()?std::string():" from "+chosen.filename().string())
                <<(replacement->use_original_alpha?" alpha=original":"")<<"\n";
        }
        s.cache[id]=replacement;s.last_use[id]=++s.tick;return replacement;
    }catch(const std::exception& ex){std::cerr<<"[overrides] "<<ex.what()<<"; original texture retained\n";return {};}
}
}
