#include "../host/override_pose.hpp"
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace renegade::overrides;
int main(){
    unsigned checks=0;auto check=[&](bool v,const char* why){++checks;if(!v)throw std::runtime_error(why);};
    try {
        PoseStore store;PoseMatrix m{1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1},camera=m;
        PoseIdentity a{{1,2,3,4,5,6},10,11},b=a;b.context=20;
        auto pose=[&](PoseIdentity id,float x,float y){auto first=m;first[12]=x;auto second=m;second[13]=y;
            store.submit(id,2,0,first,camera);return store.submit(id,2,1,second,camera);};
        check(!store.submit(a,2,0,m,camera),"Incomplete pose is not published");
        check(!store.match(a.resource,0,{1,0,0,0,1,0,0,0,1,0,0,0}),"Incomplete pose cannot match");
        auto first=store.submit(a,2,1,m,camera);check(bool(first),"Complete pose published");
        auto second=pose(b,10,20);check(first->bones[0][12]==0,"Later actor cannot overwrite old pose");
        check(store.match(a.resource,0,first->worlds[0])==first,"Delayed first actor draw retains own pose");
        check(store.match(a.resource,0,second->worlds[0])==second,"Second actor draw selects its pose");
        check(!store.match(a.resource,0,second->worlds[0]),"Consumed part cannot replay stale pose");
        store.clear();auto ambiguous=pose(a,0,1);pose(b,0,2);
        check(!store.match(a.resource,0,ambiguous->worlds[0]),"Shared root with different limbs is ambiguous");
        store.clear();auto exact=pose(a,0,1);pose(b,0,1);
        check(bool(store.match(a.resource,0,exact->worlds[0])),"Equivalent complete poses may match");
        store.clear();store.submit(a,2,0,m,camera);
        check(!store.submit(b,2,1,m,camera),"Interleaved identity is rejected");
        check(!store.submit(a,2,1,m,camera),"Interrupted batch cannot resume");
        auto invalid=m;invalid[0]=std::numeric_limits<float>::quiet_NaN();
        check(!store.submit(a,1,0,invalid,camera),"Nonfinite matrix rejected");
        check(!store.submit(a,257,0,m,camera),"Bone budget enforced");
        auto expired=pose(a,42,42);
        for(unsigned i=0;i<PoseStore::capacity;++i)pose(a,100+i,100+i);
        check(!store.match(a.resource,0,expired->worlds[0]),"Bounded store evicts old association");
        check(expired->bones[0][12]==42,"External immutable pose survives eviction");
        auto wrong=a.resource;wrong[1]++;
        auto live=pose(a,500,500);
        check(!store.match(wrong,0,live->worlds[0]),"Reused allocation key cannot match");
        store.clear();store.submit(a,3,0,m,camera);
        check(!store.submit(a,3,2,m,camera),"Missing middle bone invalidates batch");
        check(!store.submit(a,3,1,m,camera),"Invalidated batch stays unpublished");
        auto translated_camera=camera;translated_camera[12]=10;
        auto translated_bone=m;translated_bone[13]=3;
        auto transformed=store.submit(a,1,0,translated_bone,translated_camera);
        check(transformed&&transformed->worlds[0][9]==10&&transformed->worlds[0][10]==3,
              "Camera composition preserves expected translation axes");
        auto quantized=transformed->worlds[0];quantized[9]+=0.0001f;
        check(bool(store.match(a.resource,0,quantized)),"GE-sized float quantization is tolerated");
        auto huge=m;huge[0]=std::numeric_limits<float>::max();
        check(!store.submit(a,1,0,huge,huge),"Overflowing composed matrix is rejected");
        std::cout<<checks<<" pose checks passed\n";return 0;
    }catch(const std::exception& e){std::cerr<<"After "<<checks<<" checks: "<<e.what()<<'\n';return 1;}
}
