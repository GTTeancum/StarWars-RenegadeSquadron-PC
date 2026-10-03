#pragma once
#include <chrono>

namespace renegade {
// Sleeps until target with roughly millisecond accuracy, then spins briefly.
void precise_sleep_until(std::chrono::steady_clock::time_point target);
}
