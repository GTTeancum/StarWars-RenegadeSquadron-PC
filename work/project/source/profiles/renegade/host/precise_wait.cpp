#include "precise_wait.hpp"
#include <thread>
#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

namespace renegade {
// std::this_thread::sleep_until on Windows wakes on the system timer tick
// (15.6 ms unless some process raised the resolution), so a frame limiter built
// on it oversleeps by several milliseconds and misses 60 Hz. A high-resolution
// waitable timer (Windows 10 1803+) wakes within about a millisecond of the
// requested time without changing the global timer resolution.
void precise_sleep_until(std::chrono::steady_clock::time_point target) {
    constexpr auto spin_margin = std::chrono::microseconds(500);
    auto now = std::chrono::steady_clock::now();
    if (target <= now) return;
#if defined(_WIN32)
    static HANDLE timer = [] {
        HANDLE handle = CreateWaitableTimerExW(nullptr, nullptr,
            CREATE_WAITABLE_TIMER_HIGH_RESOLUTION, TIMER_ALL_ACCESS);
        if (handle == nullptr) handle = CreateWaitableTimerExW(nullptr, nullptr, 0, TIMER_ALL_ACCESS);
        return handle;
    }();
    if (timer != nullptr && target - now > spin_margin) {
        const auto wait = std::chrono::duration_cast<std::chrono::nanoseconds>(target - now - spin_margin);
        LARGE_INTEGER due{};
        due.QuadPart = -static_cast<LONGLONG>(wait.count() / 100);  // relative, 100 ns units
        if (due.QuadPart < 0 && SetWaitableTimer(timer, &due, 0, nullptr, nullptr, FALSE))
            WaitForSingleObject(timer, INFINITE);
    }
#else
    if (target - now > spin_margin) std::this_thread::sleep_until(target - spin_margin);
#endif
    while (std::chrono::steady_clock::now() < target) std::this_thread::yield();
}
} // namespace renegade
