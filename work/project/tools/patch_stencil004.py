from pathlib import Path
r=Path('/mnt/data/renegade/intake/sources/PSPRecomp');v=r/'profiles/vcs/host';p=v/'ge_renderer.cpp';s=p.read_text()
def replace(old,new,count=1):
 global s
 assert s.count(old)==count,(old[:80],s.count(old),count)
 s=s.replace(old,new)
header='''#pragma once
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
'''
(v/'ge_stencil.hpp').write_text(header)
s='#include "ge_stencil.hpp"\n'+s
replace('    bool alpha_test_enabled{};','    GeStencilState stencil{};\n    bool alpha_test_enabled{};')
replace('    setup.alpha_test_enabled = (data24(commands[0x22u]) & 1u) != 0u;', '    setup.stencil = decode_ge_stencil(commands);\n    setup.alpha_test_enabled = (data24(commands[0x22u]) & 1u) != 0u;')
replace('constexpr std::array<std::uint8_t, 23> regs{{','constexpr std::array<std::uint8_t, 26> regs{{')
replace('0xDE,0xE7,0xDF,0x21,0xE0,0xE1,0xDB,0x22,0xC9,0xCA,0x00','0xDE,0xE7,0xDF,0x21,0xE0,0xE1,0xDB,0x22,0xC9,0xCA,0x24,0xDC,0xDD,0x00')
# Exact packed write masks rather than treating each nonzero channel as all masked.
start=s.index('    const Color old = read_color_raw(pixel, format);',s.index('void write_color_raw'))
end=s.index('\n}',start)
s=s[:start]+'''    const auto old = std::uint16_t(pixel[0] | (std::uint16_t(pixel[1])<<8));
    const auto mask = pack16(unpack32(write_mask), format);
    const auto value = std::uint16_t((old & mask) | (pack16(color,format) & ~mask));
    pixel[0] = static_cast<std::uint8_t>(value);
    pixel[1] = static_cast<std::uint8_t>(value >> 8u);'''+s[end:]
start=s.index('        // PSP color masks are expressed',s.index('void write_color('));end=s.index('\n    }',start)
s=s[:start]+'''        const auto mask = pack16(unpack32(write_mask),format);
        const auto old = memory.aot_load16(address);
        memory.aot_store16(address,std::uint16_t((old & mask) | (pack16(color,format) & ~mask)));'''+s[end:]
replace('    if (setup.depth_stride == 0u) return true;','    if (setup.depth_stride == 0u || (setup.clear_mode && !clear_depth)) return true;')
# Both raster paths use the same ordered alpha/stencil/depth/color commit.
helper='''// Alpha rejection has already happened. Stencil rejection MUST precede a
// depth-buffer write. Blending uses the old destination alpha, not the new
// stencil value; only the final alpha channel is supplied by the stencil op.
bool commit_fragment(psprecomp::GuestMemory& memory, const FragmentSetup& setup,
                     std::int32_t x, std::int32_t y, std::uint16_t z, Color source,
                     GeRenderStats& stats, bool depth_resolved=false) {
    const auto index=std::size_t(y)*setup.framebuffer_stride+std::size_t(x);
    const auto address=setup.framebuffer_base+std::uint32_t(index*setup.framebuffer_bpp);
    auto* pixel=setup.color_pixels ? setup.color_pixels+index*setup.framebuffer_bpp : nullptr;
    if(!pixel && !memory.contains(address,setup.framebuffer_bpp)) return false;
    const Color destination=pixel ? read_color_raw(pixel,setup.framebuffer_format)
                                  : read_color(memory,address,setup.framebuffer_format);
    const auto write=[&](Color color,std::uint32_t mask) {
        if(pixel) write_color_raw(pixel,setup.framebuffer_format,color,mask);
        else write_color(memory,address,setup.framebuffer_format,color,mask);
    };
    const bool stencil=setup.stencil.enabled && !setup.clear_mode;
    const auto old_alpha=std::uint8_t(setup.framebuffer_format ? destination.a : 0);
    const auto apply=[&](unsigned operation) {
        return ge_stencil_operation(setup.framebuffer_format,operation,old_alpha,setup.stencil.reference);
    };
    const auto rejected=[&](unsigned operation) {
        Color changed=destination; changed.a=apply(operation);
        write(changed,setup.write_mask|0x00ffffffu);
    };
    if(stencil && !ge_stencil_compare(setup.stencil,old_alpha)) {
        rejected(setup.stencil.fail); return false;
    }
    if(!depth_resolved && !depth_test_and_write(memory,setup,x,y,z,setup.clear_mode&&setup.clear_depth)) {
        if(stencil) rejected(setup.stencil.zfail);
        return false;
    }
    if(setup.clear_mode) {
        if(!setup.clear_color) { source.r=destination.r; source.g=destination.g; source.b=destination.b; }
        if(!setup.clear_alpha) source.a=destination.a;
    } else {
        source=blend_pixel(source,destination,setup);
        source.a=stencil ? apply(setup.stencil.zpass) : destination.a;
    }
    write(source,setup.clear_mode ? 0u : setup.write_mask);
    ++stats.pixels_written;
    return true;
}

'''
place=s.index('void rasterize_rectangle(');s=s[:place]+helper+s[place:]
start=s.index('            if (!depth_test_and_write(memory, setup, x, y, z, clear_mode && clear_depth)) continue;',s.index('void rasterize_rectangle('))
end=s.index('            ++row_stats.pixels_written;',start)+len('            ++row_stats.pixels_written;')
s=s[:start]+'            commit_fragment(memory,setup,x,y,z,source,row_stats);'+s[end:]
replace('return setup.clear_mode || !setup.alpha_test_enabled;','return setup.clear_mode || (!setup.alpha_test_enabled && !setup.stencil.enabled);')
start=s.index('    if (!depth_before_shading &&',s.index('bool write_fragment('));end=s.index('\n}',start)
s=s[:start]+'''    return commit_fragment(memory,setup,x,y,z,source,stats,depth_before_shading);'''+s[end:]
p.write_text(s)
print('Stencil state, ordered commit, cache keys, packed masks patched')
