from pathlib import Path
r=Path('/mnt/data/renegade');s=r/'intake/sources/PSPRecomp';p=s/'profiles/renegade/host/psp_services.cpp'
t=p.read_text();start=t.index('//\n// There was no frame limiter anywhere');end=t.index('\nbool execute_ge_list(',start)
t=t[:start]+'''// Renegade host pacing is a ceiling on presentation rate, not a PSP clock.
// Only modeled scheduler/wait events advance virtual_time_us. A slow renderer
// or a diagnostic host pause must not change guest physics or replay timing.
struct FramePacingState {
    bool anchored{};
    std::chrono::steady_clock::time_point wall_anchor{};
    std::uint64_t guest_anchor{};
};
FramePacingState frame_pacing{};

void limit_frame_rate() {
    static const bool enabled = [] {
        const char *text = std::getenv("PSPRECOMP_FRAME_LIMIT");
        return text == nullptr || (*text != '\\0' && std::strcmp(text, "0") != 0);
    }();
    if (!enabled) return;
    const auto now = std::chrono::steady_clock::now();
    const auto anchor = [&] {
        frame_pacing = FramePacingState{true, now, virtual_time_us};
    };
    // Reset after a new runtime or a discontinuous guest clock, rather than
    // performing an unsigned subtraction or constructing an absurd deadline.
    constexpr std::uint64_t maximum_paced_gap_us = 3'600'000'000ull;
    if (!frame_pacing.anchored || virtual_time_us < frame_pacing.guest_anchor ||
        virtual_time_us - frame_pacing.guest_anchor > maximum_paced_gap_us) {
        anchor();
        return;
    }
    const auto target = frame_pacing.wall_anchor + std::chrono::microseconds(
        virtual_time_us - frame_pacing.guest_anchor);
    if (now >= target) {
        // Forgive host lateness without advancing PSP time or accumulating a
        // catch-up burst. At low host throughput the guest runs more slowly in
        // wall time; real-time performance is measured separately.
        anchor();
        return;
    }
    constexpr auto spin_margin = std::chrono::microseconds(1500);
    if (target - now > spin_margin) std::this_thread::sleep_until(target - spin_margin);
    while (std::chrono::steady_clock::now() < target) std::this_thread::yield();
}
''' +t[end:]
needle='    virtual_time_us = 0u;\n    volatile_memory_locked'
assert t.count(needle)==1;t=t.replace(needle,'    virtual_time_us = 0u;\n    frame_pacing = {};\n    volatile_memory_locked')
idx=t.rindex('} // namespace vcs')
t=t[:idx]+'''// Separate synthetic executable: real display waits and time-query HLE.
// No game state is read or modified by this regression test.
bool run_renegade_clock_tests(std::string& error) {
    unsigned checks = 0;
    try {
        const auto check = [&](bool value, const char* message) {
            ++checks;
            if (!value) throw psprecomp::Error(message);
        };
        auto heap = std::make_unique<psprecomp::Runtime>();
        auto& r = *heap;
        auto& c = r.cpu();
        const auto invoke = [&](const char* library, std::uint32_t nid, std::uint32_t arg = 0) {
            c.pc = 0x08800100u; c.gpr[31] = 0x08800108u; c.gpr[4] = arg;
            r.invoke_import(library, nid, c);
            check(!r.stopped(), "clock regression unexpectedly stopped runtime");
            return c.gpr[2];
        };
        const auto time = [&]() -> std::uint64_t {
            invoke("ThreadManForUser", 0x82BC5777u);
            return (std::uint64_t(c.gpr[3]) << 32u) | c.gpr[2];
        };
        const auto period = virtual_vblank_period_us();
        // Run twice to verify a fresh profile resets the host pacing anchor.
        for (unsigned reset = 0; reset != 2; ++reset) {
            install_profile(r, 0x08c40000u);
            check(time() == 0, "profile clock not reset");
            check(!frame_pacing.anchored, "host pacing leaked across profile reset");
            for (unsigned frame = 1; frame <= 12; ++frame) {
                if (frame % 4 == 0) std::this_thread::sleep_for(std::chrono::milliseconds(65));
                const auto before = time();
                invoke("sceDisplay", 0x984C27E7u);
                check(time() == before + period, "host stall altered PSP VBlank time");
                check(time() == frame * period, "guest clock drifted from modeled waits");
                invoke("ThreadManForUser", 0x369ED59Du);
                check(c.gpr[2] == static_cast<std::uint32_t>(frame * period), "low clock disagrees");
            }
            invoke("ThreadManForUser", 0xCEADEB47u, 5000u); // sceKernelDelayThread
            check(time() == 12 * period + 5000u, "explicit guest delay not honored");
            invoke("sceDisplay", 0x984C27E7u);
            check(time() == 13 * period, "VBlank did not align after guest delay");
        }
        // Exercise rollback and large discontinuity guards of the actual
        // limiter, with no long sleep and no mutation of the supplied clock.
        virtual_time_us = 17u; limit_frame_rate();
        check(virtual_time_us == 17u && frame_pacing.guest_anchor == 17u, "rollback pacing guard");
        virtual_time_us = UINT64_MAX - 1u; limit_frame_rate();
        check(virtual_time_us == UINT64_MAX - 1u, "large-gap pacing changed guest time");
        check(frame_pacing.guest_anchor == virtual_time_us, "large-gap pacing failed to reanchor");
        install_profile(r, 0x08c40000u);
        std::cerr << "PASS " << checks << " modeled-clock/pacing/HLE checks\\n";
        error.clear(); return true;
    } catch (const std::exception& e) {
        error = "after " + std::to_string(checks) + " checks: " + e.what();
        return false;
    }
}
''' +t[idx:];p.write_text(t)
(s/'profiles/renegade/tests/clock004.cpp').write_text('''#include <iostream>
#include <string>
namespace vcs { bool run_renegade_clock_tests(std::string&); }
int main() {
    std::string error;
    if (!vcs::run_renegade_clock_tests(error)) { std::cerr << error << '\\n'; return 1; }
    return 0;
}
''')
p=s/'profiles/renegade/CMakeLists.txt';p.write_text(p.read_text()+'''
add_executable(renegade_clock_tests tests/clock004.cpp)
target_link_libraries(renegade_clock_tests PRIVATE renegade_services)
add_test(NAME renegade_clock_tests COMMAND renegade_clock_tests)
set_tests_properties(renegade_clock_tests PROPERTIES ENVIRONMENT "PSPRECOMP_FRAME_LIMIT=1;PSPRECOMP_WINDOW=0;PSPRECOMP_AUDIO=0")
''')
p=r/'tools/package004.py';t=p.read_text().replace("'profiles/renegade/tests/stencil004.cpp']","'profiles/renegade/tests/stencil004.cpp','profiles/renegade/tests/clock004.cpp']");p.write_text(t)
print('Clock patch and production-HLE regression added')
