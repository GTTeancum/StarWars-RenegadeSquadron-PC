#include <iostream>
#include <string>
namespace vcs {bool run_renegade_atrac_tests(std::string&);}
int main(){std::string error;if(!vcs::run_renegade_atrac_tests(error)){std::cerr<<"FAIL "<<error<<"\n";return 1;}return 0;}
