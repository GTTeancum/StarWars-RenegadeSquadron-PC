#include <iostream>
#include <string>
namespace vcs {bool run_renegade_message_tests(std::string&);}
int main(){std::string error;if(vcs::run_renegade_message_tests(error))return 0;std::cerr<<error<<"\n";return 1;}
