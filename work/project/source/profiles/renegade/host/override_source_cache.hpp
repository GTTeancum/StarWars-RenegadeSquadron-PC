#pragma once
#include "override_texture.hpp"
#include <algorithm>
#include <array>
#include <map>
#include <memory>
#include <span>
namespace renegade::overrides {
// Guest render-thread only. Compare every source/palette byte; sampling could
// miss animated texels or palette edits. Replacement ownership stays with Store.
class SourceTextureCache {
public:
    using Key=std::array<std::uint32_t,14>;
    std::size_t hits{},misses{};
    template<class Decode> std::shared_ptr<const Texture> lookup(const Key& key,
        std::span<const std::uint8_t> source,std::span<const std::uint8_t> palette,Decode decode){
        auto it=entries_.find(key);
        if(it!=entries_.end()){
            auto& entry=it->second;
            if(std::ranges::equal(entry.source,source)&&std::ranges::equal(entry.palette,palette)){
                auto result=entry.replacement.lock();
                if(result||!entry.had_replacement){++hits;return result;}
            }
            bytes_-=entry.source.size()+entry.palette.size();entries_.erase(it);
        }
        ++misses;auto result=decode();
        const auto size=source.size()+palette.size();
        if(size>budget_)return result;
        if(entries_.size()>=512||bytes_+size>budget_){entries_.clear();bytes_=0;}
        Entry entry{{source.begin(),source.end()},{palette.begin(),palette.end()},result,bool(result)};
        entries_.emplace(key,std::move(entry));bytes_+=size;return result;
    }
private:
    struct Entry {
        std::vector<std::uint8_t> source,palette;
        std::weak_ptr<const Texture> replacement;
        bool had_replacement{};
    };
    static constexpr std::size_t budget_=64u*1024u*1024u;
    std::size_t bytes_{};
    std::map<Key,Entry> entries_;
};
}
