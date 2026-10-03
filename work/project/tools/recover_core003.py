from pathlib import Path
r=Path('/mnt/data/renegade/intake/sources/PSPRecomp')
def edit(path, old,new):
 p=r/path;s=p.read_text();assert s.count(old)==1,(path,old[:80],s.count(old));p.write_text(s.replace(old,new))
# Enum appended in first patch attempt; verified before continuing.
assert 'Vi2x, VSortSign, VPartial' in (r/'include/psprecomp/decoder.hpp').read_text()
edit('src/decoder.cpp','        } else if (group >= 16u && group <= 19u) {\n            d.kind = OpcodeKind::Vf2i;','''        } else if (group == 1u && operation >= 28u) {
            d.kind = OpcodeKind::Vi2x;
            static constexpr const char *names[4]{"vi2uc", "vi2c", "vi2us", "vi2s"};
            d.mnemonic = names[operation - 28u];
        } else if (group == 2u && (operation == 0u || operation == 1u ||
                                  operation == 8u || operation == 9u || operation == 10u)) {
            d.kind = OpcodeKind::VSortSign;
            d.mnemonic = operation == 0u ? "vsrt1" : operation == 1u ? "vsrt2" :
                         operation == 8u ? "vsrt3" : operation == 9u ? "vsrt4" : "vsgn";
        } else if (group >= 16u && group <= 19u) {
            d.kind = OpcodeKind::Vf2i;''')
edit('src/decoder.cpp','    case 0x36:\n','''    case 0x35:
    case 0x3D:
        d.kind = OpcodeKind::VPartial;
        d.mnemonic = (word >> 26u) == 0x35u ? ((word & 2u) ? "lvr.q" : "lvl.q")
                                            : ((word & 2u) ? "svr.q" : "svl.q");
        break;
    case 0x36:
''')
# Include extensions through Runtime's header so every generated unit can use them.
edit('include/psprecomp/runtime.hpp','#include "psprecomp/allegrex_context.hpp"','#include "psprecomp/allegrex_context.hpp"\n#include "psprecomp/allegrex_extensions.hpp"')
edit('tools/codegen_main.cpp','    case psprecomp::OpcodeKind::Vx2i: {','''    case psprecomp::OpcodeKind::Vi2x:
    case psprecomp::OpcodeKind::VSortSign: {
        const std::uint32_t length = 1u + ((d.word >> 7u) & 1u) + (((d.word >> 15u) & 1u) << 1u);
        const auto operation = (d.word >> 16u) & 31u;
        const bool pack = d.kind == psprecomp::OpcodeKind::Vi2x;
        const bool valid = pack ? (operation < 30u ? length == 4u : (length == 2u || length == 4u))
                                : (operation == 10u || length == 4u);
        if (!valid) {
            out << "    rt.unsupported(" << psprecomp::hex32(pc) << "u, " << psprecomp::hex32(d.word)
                << "u, \\\"invalid packed/sort vector size\\\"); return;\\n";
        } else {
            out << "    psprecomp::" << (pack ? "vfpu_pack_integer" : "vfpu_sort_sign")
                << "(ctx, " << (d.word & 127u) << "u, " << ((d.word >> 8u) & 127u) << "u, "
                << length << "u, " << operation << "u);\\n";
        }
        break;
    }
    case psprecomp::OpcodeKind::VPartial: {
        const auto offset = static_cast<std::int16_t>(d.word & 0xFFFCu);
        const auto vr = ((d.word >> 16u) & 31u) | ((d.word & 1u) << 5u);
        out << "    psprecomp::vfpu_partial_memory(rt.memory(), ctx, " << reg(d.rs)
            << " + static_cast<std::uint32_t>(" << offset << "), " << vr << "u, "
            << ((d.word & 2u) ? "true" : "false") << ", "
            << ((d.word >> 26u) == 0x3Du ? "true" : "false") << ");\\n";
        break;
    }
    case psprecomp::OpcodeKind::Vx2i: {''')
# Scratchpad is its own backing allocation. Full AOT regeneration/rebuild is required.
edit('include/psprecomp/guest_memory.hpp','    static constexpr std::uint32_t kVramPhysicalBase','    static constexpr std::uint32_t kScratchpadBase = 0x00010000u;\n    static constexpr std::uint32_t kScratchpadSize = 0x00004000u;\n    static constexpr std::uint32_t kVramPhysicalBase')
edit('include/psprecomp/guest_memory.hpp','enum class Region { Vram, Ram };','enum class Region { Vram, Ram, Scratchpad };')
edit('include/psprecomp/guest_memory.hpp','    std::vector<std::uint8_t> vram_;','    std::vector<std::uint8_t> scratchpad_;\n    std::vector<std::uint8_t> vram_;')
edit('src/guest_memory.cpp',': vram_(kVramSize, 0u),',': scratchpad_(kScratchpadSize, 0u), vram_(kVramSize, 0u),')
edit('src/guest_memory.cpp','    if (is_vram_window(c) && end <=','    if (c >= kScratchpadBase && end <= static_cast<std::uint64_t>(kScratchpadBase) + kScratchpadSize)\n        return true;\n    if (is_vram_window(c) && end <=')
edit('src/guest_memory.cpp','    if (is_vram_window(c))\n        return {Region::Vram, vram_offset(c)};','    if (c >= kScratchpadBase && c < kScratchpadBase + kScratchpadSize)\n        return {Region::Scratchpad, static_cast<std::size_t>(c - kScratchpadBase)};\n    if (is_vram_window(c))\n        return {Region::Vram, vram_offset(c)};')
p=r/'src/guest_memory.cpp';s=p.read_text();assert s.count('return region == Region::Vram ? vram_ : bytes_;')==2;s=s.replace('return region == Region::Vram ? vram_ : bytes_;','return region == Region::Vram ? vram_ : region == Region::Scratchpad ? scratchpad_ : bytes_;');p.write_text(s)
print('Recreated decoder/lowering and scratchpad changes. Not yet runtime-tested.')
