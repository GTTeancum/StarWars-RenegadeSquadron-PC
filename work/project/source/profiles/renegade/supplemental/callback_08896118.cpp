#include "psprecomp/runtime.hpp"
#include <bit>
#include <cmath>
#include <cstdint>
#include <limits>

namespace psprecomp {
static const std::uint16_t kEntryIds_renegade_callback_08896118[9] = {
    1, 2, 3, 4, 5, 6, 0, 7, 8,
};
void renegade_callback_08896118_entry(Runtime &rt, AllegrexContext &ctx, std::uint16_t direct_entry_id, GuestMemory::AotFastView &aot_mem) {
    std::uint32_t jump_target = 0u;
    std::uint32_t local_transfers = 0u;
    std::uint32_t local_pc = ctx.pc;
    std::uint32_t entry_id = direct_entry_id;
LOCAL_DISPATCH:
    {
    if (entry_id == 0u) {
        const std::uint32_t entry_delta = local_pc - 0x08896118u;
        entry_id = (entry_delta < 36u && (entry_delta & 3u) == 0u) ? kEntryIds_renegade_callback_08896118[entry_delta >> 2u] : 0u;
    }
    switch (entry_id) {
    case 1u: goto L_08896118;
    case 2u: goto L_0889611C;
    case 3u: goto L_08896120;
    case 4u: goto L_08896124;
    case 5u: goto L_08896128;
    case 6u: goto L_0889612C;
    case 7u: goto L_08896134;
    case 8u: goto L_08896138;
    default:
        if (local_transfers == 0u) rt.unsupported(ctx.pc, 0u, "invalid internal function entry");
        else ctx.pc = local_pc;
        return;
    }
    }
L_08896118:
    ctx.set_gpr(2, 2227u << 16u);
    goto L_0889611C;
L_0889611C:
    ctx.set_gpr(5, ctx.gpr[4] + 0u);
    goto L_08896120;
L_08896120:
    ctx.set_gpr(4, rt.memory().aot_load32(ctx.gpr[2] + static_cast<std::uint32_t>(-25440)));
    goto L_08896124;
L_08896124:
    ctx.set_gpr(29, ctx.gpr[29] + static_cast<std::uint32_t>(-16));
    goto L_08896128;
L_08896128:
    rt.memory().aot_store32(ctx.gpr[29] + static_cast<std::uint32_t>(0), ctx.gpr[31]);
    goto L_0889612C;
L_0889612C:
    ctx.set_gpr(31, 0x08896134u);
    // nop
    ctx.pc = 0x0889609Cu;
    if (rt.invoke_chained_call(ctx, &aot_mem) && ctx.pc == 0x08896134u) goto L_08896134;
    return;
L_08896134:
    ctx.set_gpr(31, rt.memory().aot_load32(ctx.gpr[29] + static_cast<std::uint32_t>(0)));
    goto L_08896138;
L_08896138:
    jump_target = ctx.gpr[31];
    ctx.set_gpr(29, ctx.gpr[29] + static_cast<std::uint32_t>(16));
    local_pc = jump_target;
    if (++local_transfers < 2048u) { entry_id = 0u; goto LOCAL_DISPATCH; }
    ctx.pc = jump_target;
    return;
}

void renegade_callback_08896118(Runtime &rt, AllegrexContext &ctx) {
    auto aot_mem = rt.memory().aot_fast_view();
    renegade_callback_08896118_entry(rt, ctx, 0u, aot_mem);
}

void renegade_callback_08A2E2E4_entry(Runtime &rt, AllegrexContext &ctx, std::uint16_t direct_entry_id, GuestMemory::AotFastView &aot_mem) {
    std::uint32_t jump_target = 0u;
    std::uint32_t local_transfers = 0u;
    std::uint32_t local_pc = ctx.pc;
    std::uint32_t entry_id = direct_entry_id;
LOCAL_DISPATCH:
    {
    if (entry_id == 0u) {
        if (local_pc == 0x08A2E2E4u) entry_id = 1u;
        else if (local_pc == 0x08A2E310u) entry_id = 2u;
    }
    switch (entry_id) {
    case 1u: goto L_08A2E2E4;
    case 2u: goto L_08A2E310;
    default:
        if (local_transfers == 0u) rt.unsupported(ctx.pc, 0u, "invalid internal function entry");
        else ctx.pc = local_pc;
        return;
    }
    }
L_08A2E2E4:
    ctx.set_gpr(29, ctx.gpr[29] + static_cast<std::uint32_t>(-16));
    aot_mem.aot_store32(ctx.gpr[29] + static_cast<std::uint32_t>(0), ctx.gpr[31]);
    ctx.set_gpr(3, static_cast<std::uint32_t>(static_cast<std::int32_t>(static_cast<std::int16_t>(aot_mem.aot_load16(ctx.gpr[5] + static_cast<std::uint32_t>(20))))));
    ctx.set_gpr(2, static_cast<std::uint32_t>(static_cast<std::int32_t>(static_cast<std::int16_t>(aot_mem.aot_load16(ctx.gpr[4] + static_cast<std::uint32_t>(20))))));
    ctx.set_gpr(7, static_cast<std::uint32_t>(static_cast<std::int32_t>(static_cast<std::int16_t>(aot_mem.aot_load16(ctx.gpr[4] + static_cast<std::uint32_t>(18))))));
    ctx.set_gpr(9, static_cast<std::uint32_t>(static_cast<std::int32_t>(static_cast<std::int16_t>(aot_mem.aot_load16(ctx.gpr[5] + static_cast<std::uint32_t>(18))))));
    ctx.set_gpr(6, static_cast<std::uint32_t>(static_cast<std::int32_t>(static_cast<std::int16_t>(aot_mem.aot_load16(ctx.gpr[4] + static_cast<std::uint32_t>(16))))));
    ctx.set_gpr(8, static_cast<std::uint32_t>(static_cast<std::int32_t>(static_cast<std::int16_t>(aot_mem.aot_load16(ctx.gpr[5] + static_cast<std::uint32_t>(16))))));
    ctx.set_gpr(4, ctx.gpr[2] + 0u);
    ctx.set_gpr(31, 0x08A2E310u);
    ctx.set_gpr(5, ctx.gpr[3] + 0u);
    ctx.pc = 0x08A2E320u;
    if (rt.invoke_chained_call(ctx, &aot_mem) && ctx.pc == 0x08A2E310u) goto L_08A2E310;
    return;
L_08A2E310:
    ctx.set_gpr(31, aot_mem.aot_load32(ctx.gpr[29] + static_cast<std::uint32_t>(0)));
    ctx.set_gpr(2, static_cast<std::int32_t>(ctx.gpr[2]) < 1 ? 1u : 0u);
    jump_target = ctx.gpr[31];
    ctx.set_gpr(29, ctx.gpr[29] + static_cast<std::uint32_t>(16));
    local_pc = jump_target;
    if (++local_transfers < 2048u) { entry_id = 0u; goto LOCAL_DISPATCH; }
    ctx.pc = jump_target;
    return;
}

void renegade_callback_08A2E2E4(Runtime &rt, AllegrexContext &ctx) {
    auto aot_mem = rt.memory().aot_fast_view();
    renegade_callback_08A2E2E4_entry(rt, ctx, 0u, aot_mem);
}

void register_supplemental_functions(Runtime &runtime) {
    if (!runtime.has_function(0x08896118u)) runtime.register_function(0x08896118u, &renegade_callback_08896118, "renegade_callback_08896118");
    if (!runtime.has_function(0x0889611Cu)) runtime.register_function(0x0889611Cu, &renegade_callback_08896118, "renegade_callback_08896118");
    if (!runtime.has_function(0x08896120u)) runtime.register_function(0x08896120u, &renegade_callback_08896118, "renegade_callback_08896118");
    if (!runtime.has_function(0x08896124u)) runtime.register_function(0x08896124u, &renegade_callback_08896118, "renegade_callback_08896118");
    if (!runtime.has_function(0x08896128u)) runtime.register_function(0x08896128u, &renegade_callback_08896118, "renegade_callback_08896118");
    if (!runtime.has_function(0x0889612Cu)) runtime.register_function(0x0889612Cu, &renegade_callback_08896118, "renegade_callback_08896118");
    if (!runtime.has_function(0x08896134u)) runtime.register_function(0x08896134u, &renegade_callback_08896118, "renegade_callback_08896118");
    if (!runtime.has_function(0x08896138u)) runtime.register_function(0x08896138u, &renegade_callback_08896118, "renegade_callback_08896118");
    if (!runtime.has_function(0x08A2E2E4u)) runtime.register_function(0x08A2E2E4u, &renegade_callback_08A2E2E4, "renegade_callback_08A2E2E4");
    if (!runtime.has_function(0x08A2E310u)) runtime.register_function(0x08A2E310u, &renegade_callback_08A2E2E4, "renegade_callback_08A2E2E4");
}
} // namespace psprecomp
