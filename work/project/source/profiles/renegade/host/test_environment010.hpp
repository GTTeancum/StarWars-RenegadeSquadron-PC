#pragma once
#include <cstdlib>
#include <stdexcept>
namespace renegade::test010 {
// Tests must change the CRT environment read by the host, not SDL's DLL CRT.
inline void set_environment(const char* name, const char* value) {
#if defined(_WIN32)
    const int result = _putenv_s(name, value);
#else
    const int result = setenv(name, value, 1);
#endif
    if (result != 0) throw std::runtime_error("Cannot configure test environment");
}
}
