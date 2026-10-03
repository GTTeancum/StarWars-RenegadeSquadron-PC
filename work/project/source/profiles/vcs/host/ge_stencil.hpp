#pragma once
// Independent PSP framebuffer-stencil arithmetic. Register encodings are from
// PSPSDK guInternal.h/sceGuStencilFunc/sceGuStencilOp. Stencil occupies alpha;
// 565 has no storage, 5551 has one bit, 4444 four bits, 8888 eight bits.
#include <array>
#include <cstdint>
#include <algorithm>
namespace vcs {
struct GeStencilState {
    bool enabled{};
    std::uint8_t function{}, reference{}, mask{}, fail{}, zfail{}, zpass{};
};
inline GeStencilState decode_ge_stencil(const std::array<std::uint32_t,256>& c) noexcept {
    const auto test=c[0xdc], op=c[0xdd];
    return {bool(c[0x24]&1),std::uint8_t(test&7),std::uint8_t(test>>8),std::uint8_t(test>>16),
        std::uint8_t(op&7),std::uint8_t((op>>8)&7),std::uint8_t((op>>16)&7)};
}
inline bool ge_stencil_compare(const GeStencilState& s, std::uint8_t stored) noexcept {
    const unsigned ref=s.reference&s.mask, value=stored&s.mask;
    switch(s.function) {
        case 0: return false; case 1: return true;
        case 2: return ref==value; case 3: return ref!=value;
        case 4: return ref<value; case 5: return ref<=value;
        case 6: return ref>value; case 7: return ref>=value;
    }
    return false;
}
inline std::uint8_t ge_stencil_operation(unsigned format, unsigned op,
                                        std::uint8_t old_alpha, std::uint8_t reference) noexcept {
    constexpr unsigned bits[4]={0,1,4,8};
    if(format>3 || !bits[format]) return 0;
    const unsigned maximum=(1u<<bits[format])-1;
    unsigned stored=old_alpha>>(8-bits[format]);
    // Replacement is not masked by the TEST mask. The framebuffer write mask
    // is applied by the packed writer after quantization to its storage format.
    if(op==2) return reference;
    switch(op) {
        case 0: break; case 1: stored=0; break;
        case 3: stored^=maximum; break;
        case 4: stored=std::min(stored+1,maximum); break;
        case 5: stored=stored ? stored-1 : 0; break;
        default: break; // Reserved operations do not alter stored stencil.
    }
    return std::uint8_t(stored*255/maximum);
}
} // namespace vcs
