#pragma once
#include "override_pose.hpp"
#include <map>
#include <atomic>
namespace renegade::overrides {
enum class CommandDrawStatus { Pending, Original, Replaced };
struct CommandDrawState {std::atomic<CommandDrawStatus> status{CommandDrawStatus::Pending};};
// Immutable result of consuming one exact emitted command, not a matrix search.
struct CommandPose {std::shared_ptr<const PoseSnapshot> pose;std::uint64_t batch{};unsigned slot{};std::shared_ptr<CommandDrawState> draw;
    std::array<std::uint32_t,6> resource{};};
class CommandPoseStore {
    struct Batch {PoseIdentity id;unsigned count{};bool rejected{},expectations{};std::shared_ptr<const PoseSnapshot> pose;
        std::vector<bool> expected,recorded;std::shared_ptr<CommandDrawState> draw=std::make_shared<CommandDrawState>();};
    struct Tag {std::shared_ptr<Batch> batch;std::uint64_t serial{};unsigned slot{};std::uint32_t word{},va{},ia{};};
    std::mutex mutex_;
    std::map<std::uint64_t,std::shared_ptr<Batch>> batches_;
    std::map<std::uint32_t,Tag> commands_;
    std::uint64_t serial_{};
public:
    static constexpr unsigned capacity=128,command_capacity=32768;
    std::uint64_t begin(const PoseIdentity& id,unsigned count){
        std::lock_guard lock(mutex_);if(!count||count>256)return 0;
        if(batches_.size()>=capacity){auto oldest=batches_.begin();auto& retired=*oldest->second;retired.rejected=true;
            if(retired.draw->status==CommandDrawStatus::Replaced){
                // A replacement is already on screen. Pending valid commands
                // must keep suppressing its original parts after pose eviction.
                // Retain only bounded command metadata, not the heavy pose.
                retired.pose.reset();retired.expected.clear();retired.recorded.clear();retired.expectations=false;
            }else for(auto it=commands_.begin();it!=commands_.end();)if(it->second.serial==oldest->first)it=commands_.erase(it);else ++it;
            batches_.erase(oldest);}
        auto batch=std::make_shared<Batch>();batch->id=id;batch->count=count;
        batch->expected.resize(count);batch->recorded.resize(count);
        auto serial=++serial_;batches_[serial]=std::move(batch);return serial;
    }
    void reject(std::uint64_t serial){std::lock_guard lock(mutex_);if(auto it=batches_.find(serial);it!=batches_.end())it->second->rejected=true;}
    void expect(std::uint64_t serial,unsigned slot,bool populated){
        std::lock_guard lock(mutex_);auto it=batches_.find(serial);if(it==batches_.end())return;
        auto& b=*it->second;if(slot>=b.count){b.rejected=true;return;}
        b.expectations=true;b.expected[slot]=populated;
    }
    bool complete(std::uint64_t serial,std::shared_ptr<const PoseSnapshot> pose){
        std::lock_guard lock(mutex_);auto it=batches_.find(serial);if(it==batches_.end())return false;
        auto& b=*it->second;
        if(b.rejected||b.pose||!pose||pose->identity!=b.id||pose->bones.size()!=b.count){b.rejected=true;return false;}
        b.pose=std::move(pose);return true;
    }
    bool record(std::uint64_t serial,unsigned slot,std::uint32_t pc,std::uint32_t word,std::uint32_t va,std::uint32_t ia){
        std::lock_guard lock(mutex_);auto it=batches_.find(serial);if(it==batches_.end())return false;
        auto& b=*it->second;
        if(b.rejected||slot>=b.count||!pc||(pc&3)||word>>24!=4||((word>>16)&7)!=4||!(word&65535)){
            b.rejected=true;return false;}
        // Reuse of a command-buffer address invalidates its older owner, even
        // when the new command word is identical. Never reuse its pose silently.
        if(auto old=commands_.find(pc);old!=commands_.end()){
            old->second.batch->rejected=true;commands_.erase(old);
            if(b.rejected)return false;
        }
        if(commands_.size()>=command_capacity){b.rejected=true;return false;}
        commands_[pc]={it->second,serial,slot,word,va,ia};b.recorded[slot]=true;return true;
    }
    CommandPose consume(std::uint32_t pc,std::uint32_t word,std::uint32_t va,std::uint32_t ia){
        std::lock_guard lock(mutex_);auto it=commands_.find(pc);if(it==commands_.end())return {};
        auto tag=std::move(it->second);commands_.erase(it);auto& b=*tag.batch;
        const bool already_drawn=b.draw->status==CommandDrawStatus::Replaced;
        if((b.rejected&&!already_drawn)||(!b.pose&&!already_drawn)||tag.word!=word||tag.va!=va||tag.ia!=ia){b.rejected=true;return {};}
        if(b.expectations)for(unsigned i=0;i<b.count;++i)if(b.expected[i]&&!b.recorded[i]){b.rejected=true;return {};}
        return {b.pose,tag.serial,tag.slot,b.draw,b.id.resource};
    }
    void clear(){std::lock_guard lock(mutex_);batches_.clear();commands_.clear();}
};
inline CommandPoseStore command_pose_store;
}
namespace psprecomp {class Runtime;struct AllegrexContext;class GuestMemory;}
namespace renegade::overrides {
void command_submission(const PoseIdentity&,unsigned count,unsigned slot,
    std::uint32_t va,std::uint32_t ia,std::uint32_t primitive,std::shared_ptr<const PoseSnapshot>);
void reset_command_submission();
void emitted_command(psprecomp::Runtime&,const psprecomp::AllegrexContext&) noexcept;
CommandPose trace_command_pose(const psprecomp::GuestMemory&,std::uint32_t pc,std::uint32_t va,
                        std::uint32_t ia,std::uint32_t primitive) noexcept;
}
