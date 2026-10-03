#pragma once
// Independent instruction helpers, based on the PSPDEV VFPU hardware documentation.
// No interpreter/JIT dispatch or title-address behavior replacement is used here.
#include "psprecomp/allegrex_context.hpp"
#include "psprecomp/guest_memory.hpp"
#include "psprecomp/common.hpp"
#include <array>
#include <bit>
#include <cstdint>

namespace psprecomp {
inline void vfpu_pack_integer(AllegrexContext &c, std::uint32_t dst, std::uint32_t src,
                             std::uint32_t n, std::uint32_t op) {
    if (op < 28 || op > 31 || (op < 30 ? n != 4 : (n != 2 && n != 4)))
        throw Error("Invalid VFPU integer pack form");
    const unsigned group = op < 30 ? 4 : 2;
    const unsigned width = group == 4 ? 8 : 16;
    const unsigned shift = 32 - width - ((op & 1) == 0);
    const unsigned outn = n / group;
    std::array<std::uint32_t,4> values{};
    // Packing is an integer operation. Only the S-prefix swizzle is consumed;
    // abs/negate/constants and destination saturation must not alter raw bits.
    for (unsigned i=0;i<n;++i) {
        const unsigned lane=(c.vfpu_ctrl[0]>>(i*2))&3;
        values[i]=lane<n ? std::bit_cast<std::uint32_t>(c.vfpu[AllegrexContext::vfpu_vector_lane_index(src,n,lane)]) : 0;
    }
    for (unsigned i=0;i<outn;++i) {
        std::uint32_t packed=0;
        for (unsigned j=0;j<group;++j) {
            const auto raw=values[i*group+j];
            const auto piece=((op&1)==0 && (raw&0x80000000u)) ? 0u : (raw>>shift);
            packed |= (piece & (width==8 ? 0xffu : 0xffffu)) << (j*width);
        }
        if (!(c.vfpu_ctrl[2] & (1u<<(8+i))))
            c.vfpu[AllegrexContext::vfpu_vector_lane_index(dst,outn,i)]=std::bit_cast<float>(packed);
    }
    c.eat_vfpu_prefixes();
}
inline void vfpu_sort_sign(AllegrexContext &c, std::uint32_t dst, std::uint32_t src,
                           std::uint32_t n, std::uint32_t op) {
    if (n<1 || n>4 || (op!=10 && n!=4)) throw Error("Invalid VFPU sorting size");
    float in[4]{},out[4]{};c.read_vfpu_vector(in,src,n);
    if(op==10) {
        c.apply_vfpu_source_prefix(in,n,0);
        for(unsigned i=0;i<n;++i) {
            const auto bits=std::bit_cast<std::uint32_t>(in[i]);
            // Signed zero returns +0; other encodings preserve the sign as +/-1.
            out[i]=(bits&0x7fffffffu)==0 ? 0.0f : std::bit_cast<float>(0x3f800000u | (bits&0x80000000u));
        }
    } else {
        if(op!=0 && op!=1 && op!=8 && op!=9) throw Error("Invalid VFPU sort operation");
        const bool reverse=op>=8;
        const std::array<unsigned,4> partners=(op&1) ? std::array<unsigned,4>{3,2,1,0} : std::array<unsigned,4>{1,0,3,2};
        for(unsigned i=0;i<4;++i) {
            const unsigned a=std::min(i,partners[i]), b=std::max(i,partners[i]);
            const bool maximum=(i==b) != reverse;
            out[i]=std::bit_cast<float>(AllegrexContext::vfpu_minmax_bits(
                std::bit_cast<std::uint32_t>(in[a]),std::bit_cast<std::uint32_t>(in[b]),maximum));
        }
    }
    c.write_vfpu_vector_with_destination_prefix(out,dst,n);
}
inline void vfpu_partial_memory(GuestMemory &m, AllegrexContext &c, std::uint32_t address,
                                std::uint32_t vr, bool right, bool store) {
    address &= ~3u;
    const unsigned word=(address&15u)/4u;
    const unsigned count=right ? 4u-word : word+1u;
    const unsigned lane=right ? 0u : 3u-word;
    const auto first=right ? address : (address&~15u);
    if(!m.contains(first,count*4u)) throw Error("VFPU partial memory outside mapped region at "+hex32(first));
    std::array<std::uint32_t,4> data{};
    for(unsigned i=0;i<count;++i) {
        const auto index=AllegrexContext::vfpu_vector_lane_index(vr,4u,lane+i);
        data[i]=store ? std::bit_cast<std::uint32_t>(c.vfpu[index]) : m.aot_load32(first+4*i);
    }
    for(unsigned i=0;i<count;++i) {
        if(store) m.aot_store32(first+4*i,data[i]);
        else c.vfpu[AllegrexContext::vfpu_vector_lane_index(vr,4u,lane+i)]=std::bit_cast<float>(data[i]);
    }
    // Loads/stores do not consume or apply any VFPU prefixes.
}
}
