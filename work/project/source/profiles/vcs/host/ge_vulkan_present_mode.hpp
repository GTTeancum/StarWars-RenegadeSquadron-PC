#pragma once

#include <span>
#include <string_view>
#include <vulkan/vulkan.h>

namespace vcs::vulkan {
inline constexpr VkPresentModeKHR choose_present_mode(
    bool low_latency, std::span<const VkPresentModeKHR> supported) {
  if (low_latency) {
    // Prefer mailbox (no tearing). Immediate is a useful experimental
    // fallback when the surface cannot do mailbox, but may visibly tear.
    for (const auto preferred :
         {VK_PRESENT_MODE_MAILBOX_KHR, VK_PRESENT_MODE_IMMEDIATE_KHR})
      for (const auto mode : supported)
        if (mode == preferred)
          return mode;
  }
  return VK_PRESENT_MODE_FIFO_KHR; // Guaranteed by Vulkan.
}

inline constexpr std::string_view present_mode_name(VkPresentModeKHR mode) {
  switch (mode) {
  case VK_PRESENT_MODE_MAILBOX_KHR: return "mailbox";
  case VK_PRESENT_MODE_IMMEDIATE_KHR: return "immediate";
  default: return "fifo";
  }
}
}
