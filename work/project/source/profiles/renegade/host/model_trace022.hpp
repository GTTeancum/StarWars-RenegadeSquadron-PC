#pragma once
#include "psprecomp/runtime.hpp"
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <string>
#include <map>

namespace renegade {
inline std::map<std::uint32_t,std::string> model_names023;
inline void trace_model_name023(psprecomp::Runtime& rt,psprecomp::AllegrexContext& c) noexcept {
    static const char* path=std::getenv("RENEGADE_TRACE_MODELS");
    if(!path||!*path)return;
    try {
        std::string name;
        for(unsigned i=0;i<512;++i){
            if(!rt.memory().contains(c.gpr[2]+i,1))return;
            auto b=rt.memory().aot_load8(c.gpr[2]+i);
            if(!b){if(model_names023.size()<64)model_names023[c.gpr[29]]=name;return;}
            if(b<32||b>126)return;
            name+=static_cast<char>(b);
        }
    }catch(...){}
}
// Diagnostic only: observe the verified HSKN loader's successful common epilogue.
// Header and model pointers are still live before the original restores s-registers.
inline void trace_model_load022(psprecomp::Runtime& rt,psprecomp::AllegrexContext& c) noexcept {
    static const char* path=std::getenv("RENEGADE_TRACE_MODELS");
    if(!path||!*path||c.gpr[2]!=1)return;
    try {
        static unsigned count=0;if(count>=4096)return;
        auto& memory=rt.memory();
        if(!memory.contains(c.gpr[19],24)||!memory.contains(c.gpr[29]+48,4))return;
        auto model=memory.aot_load32(c.gpr[29]+48);
        if(!memory.contains(model,64))return;
        static std::ofstream file(path,std::ios::trunc);
        if(!file)return;
        auto words=[&](unsigned base,unsigned bytes){
            file<<'[';
            if(memory.contains(base,bytes))for(unsigned i=0;i<bytes;i+=4){if(i)file<<',';file<<memory.aot_load32(base+i);}
            file<<']';
        };
        file<<"{\"sequence\":"<<++count<<",\"name\":"<<std::quoted(model_names023[c.gpr[29]])<<",\"model\":"<<model<<",\"header\":";
        model_names023.erase(c.gpr[29]);
        words(c.gpr[19],24);file<<",\"object\":";words(model,64);
        file<<",\"arrays\":[";
        for(unsigned offset=20;offset<=48;offset+=4){
            if(offset!=20)file<<',';
            auto address=memory.aot_load32(model+offset);
            file<<"{\"field\":"<<offset<<",\"address\":"<<address<<",\"words\":";
            words(address,256);file<<'}';
        }
        file<<"],\"parts\":[";
        auto table=memory.aot_load32(model+20), n=memory.aot_load32(model+4);
        if(n<=128 && memory.contains(table,n*4))for(unsigned i=0;i<n;++i){
            if(i)file<<',';
            auto address=memory.aot_load32(table+i*4);
            file<<"{\"index\":"<<i<<",\"address\":"<<address<<",\"words\":";
            words(address,256);file<<'}';
        }
        file<<"]}\n";file.flush();
    }catch(...){ /* A diagnostic failure must never alter guest execution. */ }
}
}
