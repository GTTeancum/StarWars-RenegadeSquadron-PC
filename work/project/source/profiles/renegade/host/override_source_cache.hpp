#pragma once
#include "override_texture.hpp"
#include <algorithm>
#include <array>
#include <map>
#include <memory>
#include <span>
#include <vector>
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
                if(result||!entry.had_replacement){++hits;entry.last_use=++tick_;return result;}
            }
            bytes_-=entry.source.size()+entry.palette.size();entries_.erase(it);
        }
        ++misses;auto result=decode();
        const auto size=source.size()+palette.size();
        if(size>budget_)return result;
        if(entries_.size()>=max_entries_||bytes_+size>budget_){
            // drop the least recently used quarter, not everything (avoids re-decoding the whole set)
            std::vector<std::pair<std::uint64_t,Key>> order;order.reserve(entries_.size());
            for(const auto& [k,e]:entries_)order.emplace_back(e.last_use,k);
            std::sort(order.begin(),order.end());
            for(const auto& [used,k]:order){
                if(entries_.size()<=max_entries_/4*3&&bytes_+size<=budget_/4*3)break;
                auto it2=entries_.find(k);bytes_-=it2->second.source.size()+it2->second.palette.size();entries_.erase(it2);
            }
        }
        Entry entry{{source.begin(),source.end()},{palette.begin(),palette.end()},result,bool(result),++tick_};
        entries_.emplace(key,std::move(entry));bytes_+=size;return result;
    }
private:
    struct Entry {
        std::vector<std::uint8_t> source,palette;
        std::weak_ptr<const Texture> replacement;
        bool had_replacement{};
        std::uint64_t last_use{};
    };
    static constexpr std::size_t budget_=512u*1024u*1024u, max_entries_=8192;
    std::uint64_t tick_{};
    std::size_t bytes_{};
    std::map<Key,Entry> entries_;
};
}
