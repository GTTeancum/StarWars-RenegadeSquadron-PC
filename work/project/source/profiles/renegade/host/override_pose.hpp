#pragma once
#include <array>
#include <cmath>
#include <cstdint>
#include <deque>
#include <memory>
#include <mutex>
#include <vector>

namespace renegade::overrides {
using PoseMatrix=std::array<float,16>;
using PoseWorld=std::array<float,12>;
struct PoseIdentity {
    std::array<std::uint32_t,6> resource{}; // record, key, VA, IA, vertex count, index count
    std::uint32_t context{},model{};
    bool operator==(const PoseIdentity&) const = default;
};
struct PoseSnapshot {
    PoseIdentity identity;
    std::uint64_t serial{};
    std::vector<PoseMatrix> bones;
    std::vector<PoseWorld> worlds;
};
// Owned copies, never guest-memory pointers. Incomplete/interleaved batches are
// discarded. Association fails closed when one draw could belong to two poses.
class PoseStore {
    struct Entry {std::shared_ptr<const PoseSnapshot> pose;std::vector<bool> used;};
    std::mutex mutex_;
    std::deque<Entry> ready_;
    PoseSnapshot pending_;
    unsigned expected_{};
    std::uint64_t serial_{};
public:
    static constexpr unsigned capacity=128,max_bones=256;
    std::shared_ptr<const PoseSnapshot> submit(const PoseIdentity& id,unsigned count,unsigned slot,
                                             const PoseMatrix& bone,const PoseMatrix& camera) {
        std::lock_guard lock(mutex_);
        auto reject=[&](){pending_={};expected_=0;return std::shared_ptr<const PoseSnapshot>{};};
        if(!count||count>max_bones||slot>=count)return reject();
        for(float v:bone)if(!std::isfinite(v))return reject();
        for(float v:camera)if(!std::isfinite(v))return reject();
        if(slot==0){pending_={};pending_.identity=id;expected_=count;}
        if(expected_!=count||pending_.identity!=id||pending_.bones.size()!=slot)return reject();
        PoseWorld world{};
        for(unsigned j=0;j<4;++j)for(unsigned i=0;i<3;++i){
            float value=0;for(unsigned k=0;k<4;++k)value+=camera[k*4+i]*bone[j*4+k];
            if(!std::isfinite(value))return reject();world[j*3+i]=value;
        }
        pending_.bones.push_back(bone);pending_.worlds.push_back(world);
        if(slot+1!=count)return {};
        pending_.serial=++serial_;
        auto snapshot=std::make_shared<const PoseSnapshot>(std::move(pending_));
        pending_={};expected_=0;
        if(ready_.size()==capacity)ready_.pop_front();
        ready_.push_back({snapshot,std::vector<bool>(count)});
        return snapshot;
    }
    std::shared_ptr<const PoseSnapshot> match(const std::array<std::uint32_t,6>& resource,
                                            unsigned slot,const PoseWorld& world) {
        std::lock_guard lock(mutex_);
        for(float v:world)if(!std::isfinite(v))return {};
        Entry* candidate=nullptr;
        for(auto& entry:ready_){
            const auto& p=*entry.pose;
            if(p.identity.resource!=resource||slot>=p.worlds.size()||entry.used[slot])continue;
            bool close=true;
            for(unsigned i=0;i<12;++i)
                if(std::abs(p.worlds[slot][i]-world[i])>0.0001f+std::abs(world[i])*0.00002f){close=false;break;}
            if(!close)continue;
            // Identical full poses are equivalent for deformation. Never choose
            // between poses that only happen to share the queried bone matrix.
            if(candidate&&(candidate->pose->bones!=p.bones||candidate->pose->worlds!=p.worlds))return {};
            if(!candidate)candidate=&entry;
        }
        if(!candidate)return {};
        candidate->used[slot]=true;return candidate->pose;
    }
    void clear(){std::lock_guard lock(mutex_);ready_.clear();pending_={};expected_=0;}
};
inline PoseStore diagnostic_pose_store;
// Production consumers must never share the diagnostic store: matching consumes
// an association, and diagnostic output has independent sampling limits.
inline PoseStore runtime_pose_store;
}
