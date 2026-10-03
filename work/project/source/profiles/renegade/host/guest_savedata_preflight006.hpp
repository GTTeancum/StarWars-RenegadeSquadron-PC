#pragma once
#include "savedata_io006.hpp"
#include <array>
#include <cstdint>
#include <functional>
#include <limits>
#include <stdexcept>
#include <vector>
#include <utility>
namespace renegade::savedata {
// ABI decoding stays in the native PSP service; this helper never reads the
// parameter block itself and cannot substitute for parameter-size validation.
struct GuestBuffer { std::uint32_t address=0, capacity=0, size=0; };
constexpr std::uint64_t kMaxGuestSaveBytes = 64ull * 1024 * 1024;
template<class Contains>
void preflight_save_buffers(const std::array<GuestBuffer,5>& buffers,
                            bool raw, Contains&& contains) {
    const unsigned count = raw ? 1 : 5;
    std::uint64_t total=0;
    for (unsigned i=0;i<count;++i) {
        const auto& b=buffers[i];
        if (b.size>b.capacity) throw std::invalid_argument("Savedata actual size exceeds buffer capacity");
        if (!b.size) continue;
        if (!b.address || std::uint64_t(b.address)+b.size>(std::uint64_t(1)<<32))
            throw std::invalid_argument("Savedata guest pointer is null or wraps");
        if (b.size>kMaxGuestSaveBytes-total)
            throw std::invalid_argument("Savedata aggregate payload is too large");
        total+=b.size;
        if (!contains(b.address,b.size))
            throw std::invalid_argument("Savedata guest range is not fully mapped");
    }
}
template<class Contains,class Copy>
std::vector<Blob> collect_save_buffers(const std::array<GuestBuffer,5>& buffers,
                                      const std::array<std::string,5>& names,
                                      bool raw, Contains&& contains, Copy&& copy) {
    const unsigned count=raw ? 1 : 5;
    preflight_save_buffers(buffers,raw,std::forward<Contains>(contains));
    // Validate every output name before copying guest memory, too.
    for(unsigned i=0;i<count;++i) if(i==0 || buffers[i].size) validate_component(names[i]);
    std::vector<Blob> owned;
    owned.reserve(count);
    for(unsigned i=0;i<count;++i) {
        const auto& b=buffers[i];
        if(i!=0 && b.size==0) continue; // Omitted auxiliary data is preserved.
        Blob blob{names[i],std::vector<std::uint8_t>(b.size)};
        if(b.size) copy(b.address,blob.bytes.data(),b.size);
        owned.push_back(std::move(blob));
    }
    return owned;
}
template<class Contains>
bool preflight_sizes_outputs(const std::array<std::uint32_t,3>& addresses,
                             Contains&& contains) {
    constexpr std::array<std::uint32_t,3> sizes{20,64,28};
    for(unsigned i=0;i<3;++i) {
        if(!addresses[i]) continue;
        if(std::uint64_t(addresses[i])+sizes[i]>(std::uint64_t(1)<<32) ||
           !contains(addresses[i],sizes[i])) return false;
    }
    return true;
}
}
