#include <iostream>
#include <string>
namespace vcs { bool run_renegade_clock_tests(std::string&); }
int main() {
    std::string error;
    if (!vcs::run_renegade_clock_tests(error)) { std::cerr << error << '\n'; return 1; }
    return 0;
}
