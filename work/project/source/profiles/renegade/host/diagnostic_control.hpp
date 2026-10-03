#pragma once
#include "psprecomp/runtime.hpp"
#include "framebuffer_capture.hpp"
#include <utility>
namespace renegade {
void control_vblank(psprecomp::Runtime&,const vcs::FramebufferDescription&,std::uint64_t);
std::uint32_t control_buttons(std::uint64_t);
bool control_analog(std::uint64_t,std::uint8_t&,std::uint8_t&);
}
