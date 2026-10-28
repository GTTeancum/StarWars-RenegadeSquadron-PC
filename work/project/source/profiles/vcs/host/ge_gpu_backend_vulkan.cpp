#include "ge_gpu_backend.hpp"
#include "vcs_config.hpp"
#include <windows.h>
#define VK_USE_PLATFORM_WIN32_KHR
#define VK_NO_PROTOTYPES
#include "ge_vulkan_spirv.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <tuple>
#include <vulkan/vulkan.h>

namespace vcs::vulkan {
#include "ge_gpu_backend_api.inc"
namespace {
#define VK_FUNCTIONS(X)                                                                                            \
  X(DestroyInstance)                                                                                               \
  X(EnumeratePhysicalDevices)                                                                                      \
  X(GetPhysicalDeviceProperties) X(GetPhysicalDeviceQueueFamilyProperties) X(                                      \
      GetPhysicalDeviceMemoryProperties) X(GetPhysicalDeviceFormatProperties)                                      \
      X(CreateDevice) X(GetDeviceProcAddr) X(DestroyDevice) X(GetDeviceQueue) X(                                   \
          DeviceWaitIdle) X(CreateCommandPool) X(DestroyCommandPool) X(AllocateCommandBuffers)                     \
          X(ResetCommandBuffer) X(BeginCommandBuffer) X(EndCommandBuffer) X(                                       \
              QueueSubmit) X(QueueWaitIdle) X(CreateBuffer) X(DestroyBuffer) X(GetBufferMemoryRequirements)        \
              X(AllocateMemory) X(FreeMemory) X(BindBufferMemory) X(MapMemory) X(                                  \
                  UnmapMemory) X(CreateImage) X(DestroyImage) X(GetImageMemoryRequirements)                        \
                  X(BindImageMemory) X(CreateImageView) X(DestroyImageView) X(                                     \
                      CreateSampler) X(DestroySampler) X(CreateRenderPass) X(DestroyRenderPass)                    \
                      X(CreateFramebuffer) X(DestroyFramebuffer) X(CreateShaderModule) X(                          \
                          DestroyShaderModule) X(CreateDescriptorSetLayout) X(DestroyDescriptorSetLayout)          \
                          X(CreateDescriptorPool) X(DestroyDescriptorPool) X(                                      \
                              AllocateDescriptorSets) X(FreeDescriptorSets) X(UpdateDescriptorSets)                \
                              X(CreatePipelineLayout) X(DestroyPipelineLayout) X(                                  \
                                  CreateGraphicsPipelines) X(DestroyPipeline)                                      \
                                  X(CmdPipelineBarrier) X(CmdCopyBufferToImage) X(                                 \
                                      CmdCopyImageToBuffer) X(CmdBeginRenderPass)                                  \
                                      X(CmdEndRenderPass) X(CmdBindPipeline) X(                                    \
                                          CmdSetViewport) X(CmdSetScissor) X(CmdSetBlendConstants)                 \
                                          X(CmdSetStencilReference) X(                                             \
                                              CmdBindVertexBuffers) X(CmdBindDescriptorSets)                       \
                                              X(CmdPushConstants) X(CmdDraw) X(                                    \
                                                  CmdClearAttachments) X(CmdClearColorImage)                       \
                                                  X(CmdClearDepthStencilImage) X(                                  \
                                                      CmdBlitImage) X(CmdCopyImage)                                \
                                                      X(CreateWin32SurfaceKHR) X(                                  \
                                                          DestroySurfaceKHR) X(GetPhysicalDeviceSurfaceSupportKHR) \
                                                          X(GetPhysicalDeviceSurfaceCapabilitiesKHR) X(            \
                                                              GetPhysicalDeviceSurfaceFormatsKHR)                  \
                                                              X(CreateSwapchainKHR) X(                             \
                                                                  DestroySwapchainKHR)                             \
                                                                  X(GetSwapchainImagesKHR) X(                      \
                                                                      AcquireNextImageKHR)                         \
                                                                      X(QueuePresentKHR)                           \
                                                                          X(CreateSemaphore)                       \
                                                                              X(DestroySemaphore)
#define DECLARE(name) PFN_vk##name vk##name{};
VK_FUNCTIONS(DECLARE)
#undef DECLARE
PFN_vkGetInstanceProcAddr getProc{};
void check(VkResult r, const char *op) {
  if (r != VK_SUCCESS)
    throw std::runtime_error(std::string(op) + " (VkResult " +
                             std::to_string(r) + ")");
}
#define VK_CHECK(x) check(x, #x)
struct Buffer {
  VkBuffer handle{};
  VkDeviceMemory memory{};
  void *mapped{};
  VkDeviceSize size{};
};
struct Image {
  VkImage handle{};
  VkDeviceMemory memory{};
  VkImageView view{};
  VkImageLayout layout{VK_IMAGE_LAYOUT_UNDEFINED};
  unsigned width{}, height{}, levels{1};
};
struct Texture {
  Image image;
  VkSampler sampler{};
  VkDescriptorSet set{};
  std::uint64_t signature{}, last_use{};
  std::size_t bytes{};
};
struct Target {
  Image color, depth, multisample;
  VkFramebuffer framebuffer{};
};
struct Push {
  std::array<float, 4> rows[4];
  std::array<float, 4> uv;
  std::array<unsigned, 4> control;
  std::array<float, 4> fog;
  std::array<unsigned, 4> flags;
};
static_assert(sizeof(Push) == 128);
struct State {
  HMODULE loader{};
  VkInstance instance{};
  VkPhysicalDevice gpu{};
  VkDevice device{};
  VkQueue queue{};
  unsigned family{}, width{480}, height{272};
  VkSampleCountFlagBits samples{VK_SAMPLE_COUNT_1_BIT};
  VkCommandPool pool{};
  VkCommandBuffer cmd{};
  bool recording{}, rendering{}, enabled{}, failed{}, smooth{};
  VkRenderPass pass{};
  VkDescriptorSetLayout set_layout{};
  VkDescriptorPool descriptors{};
  VkPipelineLayout layout{};
  VkShaderModule vs{}, ps{};
  Buffer geometry, readback;
  VkDeviceSize used{};
  std::map<std::uint64_t, Texture> textures;
  std::map<unsigned, Target> targets;
  std::map<std::string, VkPipeline> pipelines;
  Texture white;
  Target *active{};
  unsigned display{}, owned{};
  std::uint64_t frame{};
  HWND window{};
  VkSurfaceKHR surface{};
  VkSwapchainKHR swap{};
  VkSemaphore acquired{}, finished{};
  unsigned sw{}, sh{};
  std::vector<VkImage> swap_images;
  std::vector<std::byte> pixels, last_texture;
  GeGpuBackendReport report;
  VkPhysicalDeviceMemoryProperties memory{};
} s;
unsigned address(unsigned a) { return a & 0x03ffffffu; }
void error(const std::exception &e) {
  s.failed = true;
  s.report.message = e.what();
  std::cerr << "[vulkan] " << e.what() << '\n';
}
unsigned memory_type(unsigned bits, VkMemoryPropertyFlags flags) {
  for (unsigned i = 0; i < s.memory.memoryTypeCount; ++i)
    if ((bits & (1u << i)) &&
        (s.memory.memoryTypes[i].propertyFlags & flags) == flags)
      return i;
  throw std::runtime_error("No compatible Vulkan memory type");
}
Buffer buffer(VkDeviceSize bytes, VkBufferUsageFlags usage) {
  Buffer b;
  b.size = bytes;
  VkBufferCreateInfo ci{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
  ci.size = bytes;
  ci.usage = usage;
  VK_CHECK(vkCreateBuffer(s.device, &ci, nullptr, &b.handle));
  VkMemoryRequirements r;
  vkGetBufferMemoryRequirements(s.device, b.handle, &r);
  VkMemoryAllocateInfo ai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
  ai.allocationSize = r.size;
  ai.memoryTypeIndex =
      memory_type(r.memoryTypeBits, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
                                        VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
  VK_CHECK(vkAllocateMemory(s.device, &ai, nullptr, &b.memory));
  VK_CHECK(vkBindBufferMemory(s.device, b.handle, b.memory, 0));
  VK_CHECK(vkMapMemory(s.device, b.memory, 0, VK_WHOLE_SIZE, 0, &b.mapped));
  return b;
}
void destroy(Buffer &b) {
  if (b.mapped)
    vkUnmapMemory(s.device, b.memory);
  if (b.handle)
    vkDestroyBuffer(s.device, b.handle, nullptr);
  if (b.memory)
    vkFreeMemory(s.device, b.memory, nullptr);
  b = {};
}
Image image(unsigned w, unsigned h, unsigned levels, VkFormat format,
            VkImageUsageFlags usage, VkImageAspectFlags aspect,
            VkSampleCountFlagBits samples = VK_SAMPLE_COUNT_1_BIT) {
  Image i;
  i.width = w;
  i.height = h;
  i.levels = levels;
  VkImageCreateInfo ci{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
  ci.imageType = VK_IMAGE_TYPE_2D;
  ci.format = format;
  ci.extent = {w, h, 1};
  ci.mipLevels = levels;
  ci.arrayLayers = 1;
  ci.samples = samples;
  ci.tiling = VK_IMAGE_TILING_OPTIMAL;
  ci.usage = usage;
  VK_CHECK(vkCreateImage(s.device, &ci, nullptr, &i.handle));
  VkMemoryRequirements r;
  vkGetImageMemoryRequirements(s.device, i.handle, &r);
  VkMemoryAllocateInfo ai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
  ai.allocationSize = r.size;
  ai.memoryTypeIndex =
      memory_type(r.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
  VK_CHECK(vkAllocateMemory(s.device, &ai, nullptr, &i.memory));
  VK_CHECK(vkBindImageMemory(s.device, i.handle, i.memory, 0));
  VkImageViewCreateInfo vi{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};
  vi.image = i.handle;
  vi.viewType = VK_IMAGE_VIEW_TYPE_2D;
  vi.format = format;
  vi.subresourceRange = {aspect, 0, levels, 0, 1};
  VK_CHECK(vkCreateImageView(s.device, &vi, nullptr, &i.view));
  return i;
}
void destroy(Image &i) {
  if (i.view)
    vkDestroyImageView(s.device, i.view, nullptr);
  if (i.handle)
    vkDestroyImage(s.device, i.handle, nullptr);
  if (i.memory)
    vkFreeMemory(s.device, i.memory, nullptr);
  i = {};
}
void end_pass() {
  if (s.rendering) {
    vkCmdEndRenderPass(s.cmd);
    s.rendering = false;
  }
}
void begin() {
  if (s.recording)
    return;
  VK_CHECK(vkResetCommandBuffer(s.cmd, 0));
  VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
  bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
  VK_CHECK(vkBeginCommandBuffer(s.cmd, &bi));
  s.recording = true;
}
void submit() {
  if (!s.recording)
    return;
  end_pass();
  VK_CHECK(vkEndCommandBuffer(s.cmd));
  VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};
  si.commandBufferCount = 1;
  si.pCommandBuffers = &s.cmd;
  VK_CHECK(vkQueueSubmit(s.queue, 1, &si, VK_NULL_HANDLE));
  VK_CHECK(vkQueueWaitIdle(s.queue));
  s.recording = false;
}
void transition(Image &i, VkImageLayout layout,
                VkImageAspectFlags aspect = VK_IMAGE_ASPECT_COLOR_BIT) {
  begin();
  end_pass();
  VkImageMemoryBarrier b{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};
  b.srcAccessMask =
      i.layout == VK_IMAGE_LAYOUT_UNDEFINED
          ? 0
          : VK_ACCESS_MEMORY_READ_BIT | VK_ACCESS_MEMORY_WRITE_BIT;
  b.dstAccessMask = VK_ACCESS_MEMORY_READ_BIT | VK_ACCESS_MEMORY_WRITE_BIT;
  b.oldLayout = i.layout;
  b.newLayout = layout;
  b.srcQueueFamilyIndex = b.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
  b.image = i.handle;
  b.subresourceRange = {aspect, 0, i.levels, 0, 1};
  vkCmdPipelineBarrier(s.cmd, VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
                       VK_PIPELINE_STAGE_ALL_COMMANDS_BIT, 0, 0, nullptr, 0,
                       nullptr, 1, &b);
  i.layout = layout;
}
void destroy(Texture &t) {
  if (t.set)
    vkFreeDescriptorSets(s.device, s.descriptors, 1, &t.set);
  if (t.sampler)
    vkDestroySampler(s.device, t.sampler, nullptr);
  destroy(t.image);
  t = {};
}
void bind_texture(Texture &t, const GeGpuDrawDescriptor &d) {
  VkSamplerCreateInfo ci{VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO};
  ci.magFilter = d.texture_mag_linear || d.texture_linear ? VK_FILTER_LINEAR
                                                          : VK_FILTER_NEAREST;
  ci.minFilter = d.texture_min_linear ? VK_FILTER_LINEAR : VK_FILTER_NEAREST;
  ci.mipmapMode = d.texture_mipmap_linear ? VK_SAMPLER_MIPMAP_MODE_LINEAR
                                          : VK_SAMPLER_MIPMAP_MODE_NEAREST;
  ci.addressModeU = d.texture_clamp_u ? VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE
                                      : VK_SAMPLER_ADDRESS_MODE_REPEAT;
  ci.addressModeV = d.texture_clamp_v ? VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE
                                      : VK_SAMPLER_ADDRESS_MODE_REPEAT;
  ci.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
  ci.maxLod = d.texture_mipmap_enabled ? float(t.image.levels - 1) : 0.f;
  VK_CHECK(vkCreateSampler(s.device, &ci, nullptr, &t.sampler));
  VkDescriptorSetAllocateInfo ai{
      VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
  ai.descriptorPool = s.descriptors;
  ai.descriptorSetCount = 1;
  ai.pSetLayouts = &s.set_layout;
  VK_CHECK(vkAllocateDescriptorSets(s.device, &ai, &t.set));
  VkDescriptorImageInfo ii{VK_NULL_HANDLE, t.image.view,
                           VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL};
  VkDescriptorImageInfo sm{t.sampler, VK_NULL_HANDLE,
                           VK_IMAGE_LAYOUT_UNDEFINED};
  VkWriteDescriptorSet writes[2]{};
  for (unsigned n = 0; n < 2; ++n) {
    writes[n].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
    writes[n].dstSet = t.set;
    writes[n].dstBinding = n;
    writes[n].descriptorCount = 1;
    writes[n].descriptorType =
        n ? VK_DESCRIPTOR_TYPE_SAMPLER : VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE;
    writes[n].pImageInfo = n ? &sm : &ii;
  }
  vkUpdateDescriptorSets(s.device, 2, writes, 0, nullptr);
}
std::uint64_t key(const GeGpuDrawDescriptor &d) {
  if (d.texture_cache_key_hint)
    return d.texture_cache_key_hint;
  std::uint64_t k = 1469598103934665603ull;
  auto add = [&](std::uint64_t v) { k = (k ^ v) * 1099511628211ull; };
  add(d.texture_address);
  add(d.texture_width);
  add(d.texture_height);
  add(d.texture_format);
  add(d.texture_buffer_width);
  add(d.clut_address);
  add(d.clut_checksum);
  add(d.clut_format);
  add(d.clut_shift);
  add(d.clut_mask);
  add(d.clut_start);
  add(d.texture_swizzled);
  add(d.texture_min_linear);
  add(d.texture_mag_linear);
  add(d.texture_linear);
  add(d.texture_clamp_u);
  add(d.texture_clamp_v);
  add(d.texture_max_level);
  add(d.texture_mipmap_enabled);
  add(d.texture_mipmap_linear);
  for (auto a : d.texture_level_addresses)
    add(a);
  for (auto a : d.texture_level_buffer_widths)
    add(a);
  for (auto a : d.texture_level_widths)
    add(a);
  for (auto a : d.texture_level_heights)
    add(a);
  add(d.texture_level_mode);
  add(unsigned(d.texture_level_offset16));
  add(std::bit_cast<unsigned>(d.texture_lod_slope));
  return k;
}
void upload(Texture &t, const GeGpuDrawDescriptor &d, unsigned w, unsigned h,
            unsigned levels, std::vector<std::byte> pixels) {
  submit();
  destroy(t);
  t.image = image(w, h, levels, VK_FORMAT_R8G8B8A8_UNORM,
                  VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT,
                  VK_IMAGE_ASPECT_COLOR_BIT);
  Buffer staging = buffer(pixels.size(), VK_BUFFER_USAGE_TRANSFER_SRC_BIT);
  std::memcpy(staging.mapped, pixels.data(), pixels.size());
  transition(t.image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL);
  std::vector<VkBufferImageCopy> regions;
  VkDeviceSize offset = 0;
  for (unsigned n = 0; n < levels; ++n) {
    VkBufferImageCopy r{};
    r.bufferOffset = offset;
    r.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, n, 0, 1};
    r.imageExtent = {std::max(1u, w >> n), std::max(1u, h >> n), 1};
    offset += VkDeviceSize(r.imageExtent.width) * r.imageExtent.height * 4;
    regions.push_back(r);
  }
  vkCmdCopyBufferToImage(s.cmd, staging.handle, t.image.handle, t.image.layout,
                         unsigned(regions.size()), regions.data());
  transition(t.image, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL);
  submit();
  destroy(staging);
  bind_texture(t, d);
  t.signature = d.texture_content_signature;
  t.last_use = s.frame;
  t.bytes = pixels.size();
  s.last_texture.assign(pixels.begin(),
                        pixels.begin() + std::size_t(w) * h * 4);
  ++s.report.texture_image_uploads;
  ++s.report.decoded_texture_uploads;
  s.report.decoded_texture_bytes += t.bytes;
}
Target &target(unsigned addr) {
  auto [it, created] = s.targets.try_emplace(address(addr));
  auto &t = it->second;
  if (created) {
    t.color = image(
        s.width, s.height, 1, VK_FORMAT_R8G8B8A8_UNORM,
        VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT |
            VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT,
        VK_IMAGE_ASPECT_COLOR_BIT);
    t.depth = image(s.width, s.height, 1, VK_FORMAT_D32_SFLOAT_S8_UINT,
                    VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT |
                        VK_IMAGE_USAGE_TRANSFER_DST_BIT,
                    VK_IMAGE_ASPECT_DEPTH_BIT | VK_IMAGE_ASPECT_STENCIL_BIT,
                    s.samples);
    transition(t.color, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL);
    VkClearColorValue black{{0, 0, 0, 1}};
    VkImageSubresourceRange cr{VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
    vkCmdClearColorImage(s.cmd, t.color.handle, t.color.layout, &black, 1, &cr);
    transition(t.depth, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
               VK_IMAGE_ASPECT_DEPTH_BIT | VK_IMAGE_ASPECT_STENCIL_BIT);
    VkClearDepthStencilValue ds{1.f, 0};
    cr.aspectMask = VK_IMAGE_ASPECT_DEPTH_BIT | VK_IMAGE_ASPECT_STENCIL_BIT;
    vkCmdClearDepthStencilImage(s.cmd, t.depth.handle, t.depth.layout, &ds, 1,
                                &cr);
    transition(t.depth, VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL,
               cr.aspectMask);
    if (s.samples != VK_SAMPLE_COUNT_1_BIT) {
      t.multisample = image(s.width, s.height, 1, VK_FORMAT_R8G8B8A8_UNORM,
                            VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT |
                                VK_IMAGE_USAGE_TRANSFER_DST_BIT,
                            VK_IMAGE_ASPECT_COLOR_BIT, s.samples);
      transition(t.multisample, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL);
      cr.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
      vkCmdClearColorImage(s.cmd, t.multisample.handle, t.multisample.layout,
                           &black, 1, &cr);
    }
    VkImageView views[] = {
        s.samples == VK_SAMPLE_COUNT_1_BIT ? t.color.view : t.multisample.view,
        t.depth.view, t.color.view};
    VkFramebufferCreateInfo ci{VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO};
    ci.renderPass = s.pass;
    ci.attachmentCount = s.samples == VK_SAMPLE_COUNT_1_BIT ? 2 : 3;
    ci.pAttachments = views;
    ci.width = s.width;
    ci.height = s.height;
    ci.layers = 1;
    VK_CHECK(vkCreateFramebuffer(s.device, &ci, nullptr, &t.framebuffer));
  }
  return t;
}
void render(Target &t) {
  if (s.rendering && s.active == &t)
    return;
  end_pass();
  transition(t.color, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL);
  if (t.multisample.handle)
    transition(t.multisample, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL);
  VkRenderPassBeginInfo bi{VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO};
  bi.renderPass = s.pass;
  bi.framebuffer = t.framebuffer;
  bi.renderArea.extent = {s.width, s.height};
  vkCmdBeginRenderPass(s.cmd, &bi, VK_SUBPASS_CONTENTS_INLINE);
  s.rendering = true;
  s.active = &t;
}
VkCompareOp compare(unsigned f) {
  const VkCompareOp ops[] = {
      VK_COMPARE_OP_NEVER,   VK_COMPARE_OP_ALWAYS,
      VK_COMPARE_OP_EQUAL,   VK_COMPARE_OP_NOT_EQUAL,
      VK_COMPARE_OP_LESS,    VK_COMPARE_OP_LESS_OR_EQUAL,
      VK_COMPARE_OP_GREATER, VK_COMPARE_OP_GREATER_OR_EQUAL};
  return ops[f & 7];
}
VkStencilOp stencil(unsigned f) {
  const VkStencilOp ops[] = {VK_STENCIL_OP_KEEP,
                             VK_STENCIL_OP_ZERO,
                             VK_STENCIL_OP_REPLACE,
                             VK_STENCIL_OP_INVERT,
                             VK_STENCIL_OP_INCREMENT_AND_CLAMP,
                             VK_STENCIL_OP_DECREMENT_AND_CLAMP,
                             VK_STENCIL_OP_KEEP,
                             VK_STENCIL_OP_KEEP};
  return ops[f & 7];
}
VkBlendFactor factor(unsigned f, bool src, unsigned fix) {
  switch (f) {
  case 0:
    return src ? VK_BLEND_FACTOR_DST_COLOR : VK_BLEND_FACTOR_SRC_COLOR;
  case 1:
    return src ? VK_BLEND_FACTOR_ONE_MINUS_DST_COLOR
               : VK_BLEND_FACTOR_ONE_MINUS_SRC_COLOR;
  case 2:
    return VK_BLEND_FACTOR_SRC_ALPHA;
  case 3:
    return VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
  case 4:
    return VK_BLEND_FACTOR_DST_ALPHA;
  case 5:
    return VK_BLEND_FACTOR_ONE_MINUS_DST_ALPHA;
  case 10:
    return (fix & 0xffffff) == 0          ? VK_BLEND_FACTOR_ZERO
           : (fix & 0xffffff) == 0xffffff ? VK_BLEND_FACTOR_ONE
                                          : VK_BLEND_FACTOR_CONSTANT_COLOR;
  default:
    throw std::runtime_error("Vulkan: unsupported doubled-alpha blend factor");
  }
}
VkPipeline pipeline(const GeGpuDrawDescriptor &d) {
  std::string k;
  auto add = [&](unsigned v) {
    k.append(reinterpret_cast<const char *>(&v), sizeof(v));
  };
  add(d.clear_mode);
  add(d.clear_color);
  add(d.clear_alpha);
  add(d.clear_depth);
  add(d.depth_test_enabled);
  add(d.depth_write_enabled);
  add(d.depth_function);
  add(d.blend_enabled);
  add(d.blend_equation);
  add(d.blend_source_factor);
  add(d.blend_dest_factor);
  add(d.blend_fix_source);
  add(d.blend_fix_dest);
  add(d.color_write_mask);
  add(d.stencil.enabled);
  add(d.stencil.function);
  add(d.stencil.mask);
  add(d.stencil.fail);
  add(d.stencil.zfail);
  add(d.stencil.zpass);
  if (auto it = s.pipelines.find(k); it != s.pipelines.end())
    return it->second;
  VkPipelineShaderStageCreateInfo stages[2]{};
  for (unsigned n = 0; n < 2; ++n) {
    stages[n].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
    stages[n].stage =
        n ? VK_SHADER_STAGE_FRAGMENT_BIT : VK_SHADER_STAGE_VERTEX_BIT;
    stages[n].module = n ? s.ps : s.vs;
    stages[n].pName = n ? "PSMain" : "VSMain";
  }
  VkVertexInputBindingDescription binding{0, sizeof(GeGpuVertex),
                                          VK_VERTEX_INPUT_RATE_VERTEX};
  VkVertexInputAttributeDescription attrs[] = {
      {0, 0, VK_FORMAT_R32G32B32A32_SFLOAT, offsetof(GeGpuVertex, x)},
      {1, 0, VK_FORMAT_R8G8B8A8_UNORM, offsetof(GeGpuVertex, rgba)},
      {2, 0, VK_FORMAT_R32G32_SFLOAT, offsetof(GeGpuVertex, u)},
      {3, 0, VK_FORMAT_R32_SFLOAT, offsetof(GeGpuVertex, fog_factor)},
      {4, 0, VK_FORMAT_R32_SFLOAT, offsetof(GeGpuVertex, q)}};
  VkPipelineVertexInputStateCreateInfo vi{
      VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
  vi.vertexBindingDescriptionCount = 1;
  vi.pVertexBindingDescriptions = &binding;
  vi.vertexAttributeDescriptionCount = 5;
  vi.pVertexAttributeDescriptions = attrs;
  VkPipelineInputAssemblyStateCreateInfo ia{
      VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO};
  ia.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
  VkPipelineViewportStateCreateInfo vp{
      VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO};
  vp.viewportCount = vp.scissorCount = 1;
  VkPipelineRasterizationStateCreateInfo rs{
      VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO};
  rs.polygonMode = VK_POLYGON_MODE_FILL;
  rs.lineWidth = 1;
  rs.cullMode = VK_CULL_MODE_NONE;
  VkPipelineMultisampleStateCreateInfo ms{
      VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO};
  ms.rasterizationSamples = s.samples;
  VkPipelineDepthStencilStateCreateInfo ds{
      VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO};
  ds.depthTestEnable = d.clear_mode ? d.clear_depth : d.depth_test_enabled;
  ds.depthWriteEnable = d.clear_mode ? d.clear_depth : d.depth_write_enabled;
  ds.depthCompareOp =
      d.clear_mode ? VK_COMPARE_OP_ALWAYS : compare(d.depth_function);
  ds.stencilTestEnable = d.clear_mode ? d.clear_alpha : d.stencil.enabled;
  ds.front = {stencil(d.stencil.fail),  stencil(d.stencil.zpass),
              stencil(d.stencil.zfail), compare(d.stencil.function),
              d.stencil.mask,           (~d.color_write_mask >> 24) & 255,
              d.stencil.reference};
  if (d.clear_mode && d.clear_alpha)
    ds.front = {VK_STENCIL_OP_REPLACE,
                VK_STENCIL_OP_REPLACE,
                VK_STENCIL_OP_REPLACE,
                VK_COMPARE_OP_ALWAYS,
                255,
                255,
                0};
  ds.back = ds.front;
  VkPipelineColorBlendAttachmentState ba{};
  ba.blendEnable = d.blend_enabled && !d.clear_mode;
  for (unsigned c = 0; c < 4; ++c)
    if (d.clear_mode ? (c == 3 ? d.clear_alpha : d.clear_color)
                     : ((d.color_write_mask >> (8 * c)) & 255) != 255)
      ba.colorWriteMask |= 1u << c;
  if (ba.blendEnable) {
    ba.srcColorBlendFactor =
        factor(d.blend_source_factor, true, d.blend_fix_source);
    ba.dstColorBlendFactor =
        factor(d.blend_dest_factor, false, d.blend_fix_dest);
    const VkBlendOp ops[] = {VK_BLEND_OP_ADD, VK_BLEND_OP_SUBTRACT,
                             VK_BLEND_OP_REVERSE_SUBTRACT, VK_BLEND_OP_MIN,
                             VK_BLEND_OP_MAX};
    if (d.blend_equation > 4)
      throw std::runtime_error("Vulkan: unsupported absolute-difference blend");
    ba.colorBlendOp = ops[d.blend_equation];
    ba.srcAlphaBlendFactor = ba.srcColorBlendFactor;
    ba.dstAlphaBlendFactor = ba.dstColorBlendFactor;
    ba.alphaBlendOp = ba.colorBlendOp;
  }
  VkPipelineColorBlendStateCreateInfo cb{
      VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO};
  cb.attachmentCount = 1;
  cb.pAttachments = &ba;
  VkDynamicState dynamics[] = {
      VK_DYNAMIC_STATE_VIEWPORT, VK_DYNAMIC_STATE_SCISSOR,
      VK_DYNAMIC_STATE_BLEND_CONSTANTS, VK_DYNAMIC_STATE_STENCIL_REFERENCE};
  VkPipelineDynamicStateCreateInfo dy{
      VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO};
  dy.dynamicStateCount = 4;
  dy.pDynamicStates = dynamics;
  VkGraphicsPipelineCreateInfo ci{
      VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO};
  ci.stageCount = 2;
  ci.pStages = stages;
  ci.pVertexInputState = &vi;
  ci.pInputAssemblyState = &ia;
  ci.pViewportState = &vp;
  ci.pRasterizationState = &rs;
  ci.pMultisampleState = &ms;
  ci.pDepthStencilState = &ds;
  ci.pColorBlendState = &cb;
  ci.pDynamicState = &dy;
  ci.layout = s.layout;
  ci.renderPass = s.pass;
  VkPipeline p;
  VK_CHECK(
      vkCreateGraphicsPipelines(s.device, VK_NULL_HANDLE, 1, &ci, nullptr, &p));
  s.pipelines.emplace(k, p);
  return p;
}
void destroy_swap() {
  if (s.swap)
    vkDestroySwapchainKHR(s.device, s.swap, nullptr);
  s.swap = {};
  s.swap_images.clear();
  s.sw = s.sh = 0;
}
void ensure_swap() {
  RECT r{};
  GetClientRect(s.window, &r);
  unsigned w = unsigned(std::max(0L, r.right)),
           h = unsigned(std::max(0L, r.bottom));
  if (!w || !h)
    return;
  if (s.swap && w == s.sw && h == s.sh)
    return;
  submit();
  VK_CHECK(vkDeviceWaitIdle(s.device));
  destroy_swap();
  VkSurfaceCapabilitiesKHR caps;
  VK_CHECK(vkGetPhysicalDeviceSurfaceCapabilitiesKHR(s.gpu, s.surface, &caps));
  unsigned count = 0;
  VK_CHECK(
      vkGetPhysicalDeviceSurfaceFormatsKHR(s.gpu, s.surface, &count, nullptr));
  std::vector<VkSurfaceFormatKHR> formats(count);
  VK_CHECK(vkGetPhysicalDeviceSurfaceFormatsKHR(s.gpu, s.surface, &count,
                                                formats.data()));
  auto it = std::find_if(formats.begin(), formats.end(), [](auto f) {
    return f.format == VK_FORMAT_B8G8R8A8_UNORM ||
           f.format == VK_FORMAT_R8G8B8A8_UNORM;
  });
  if (it == formats.end())
    throw std::runtime_error("Vulkan surface has no supported UNORM format");
  if (!(caps.supportedUsageFlags & VK_IMAGE_USAGE_TRANSFER_DST_BIT))
    throw std::runtime_error("Vulkan surface cannot receive blits");
  VkSwapchainCreateInfoKHR ci{VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR};
  ci.surface = s.surface;
  ci.minImageCount = std::max(2u, caps.minImageCount);
  if (caps.maxImageCount)
    ci.minImageCount = std::min(ci.minImageCount, caps.maxImageCount);
  ci.imageFormat = it->format;
  ci.imageColorSpace = it->colorSpace;
  ci.imageExtent = caps.currentExtent.width != UINT32_MAX
                       ? caps.currentExtent
                       : VkExtent2D{std::clamp(w, caps.minImageExtent.width,
                                               caps.maxImageExtent.width),
                                    std::clamp(h, caps.minImageExtent.height,
                                               caps.maxImageExtent.height)};
  ci.imageArrayLayers = 1;
  ci.imageUsage = VK_IMAGE_USAGE_TRANSFER_DST_BIT;
  ci.preTransform = caps.currentTransform;
  ci.compositeAlpha = VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;
  for (unsigned bit = 1; !(caps.supportedCompositeAlpha & ci.compositeAlpha);
       bit <<= 1)
    ci.compositeAlpha = VkCompositeAlphaFlagBitsKHR(bit);
  ci.presentMode = VK_PRESENT_MODE_FIFO_KHR;
  ci.clipped = VK_TRUE;
  VK_CHECK(vkCreateSwapchainKHR(s.device, &ci, nullptr, &s.swap));
  s.sw = ci.imageExtent.width;
  s.sh = ci.imageExtent.height;
  VK_CHECK(vkGetSwapchainImagesKHR(s.device, s.swap, &count, nullptr));
  s.swap_images.resize(count);
  VK_CHECK(
      vkGetSwapchainImagesKHR(s.device, s.swap, &count, s.swap_images.data()));
}
void present(Target &t) {
  RECT client{};
  if (!GetClientRect(s.window, &client) || client.right <= 0 ||
      client.bottom <= 0)
    return;
  ensure_swap();
  if (!s.swap)
    return;
  unsigned index = 0;
  auto result = vkAcquireNextImageKHR(s.device, s.swap, UINT64_MAX, s.acquired,
                                      VK_NULL_HANDLE, &index);
  if (result == VK_ERROR_OUT_OF_DATE_KHR) {
    destroy_swap();
    return;
  }
  if (result != VK_SUBOPTIMAL_KHR)
    check(result, "vkAcquireNextImageKHR");
  begin();
  end_pass();
  Image swap;
  swap.handle = s.swap_images[index];
  transition(swap, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL);
  VkClearColorValue black{{0, 0, 0, 1}};
  VkImageSubresourceRange range{VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
  vkCmdClearColorImage(s.cmd, swap.handle, swap.layout, &black, 1, &range);
  transition(swap, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL);
  transition(t.color, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL);
  float scale = std::min(float(s.sw) / s.width, float(s.sh) / s.height);
  int w = int(s.width * scale), h = int(s.height * scale),
      x = (int(s.sw) - w) / 2, y = (int(s.sh) - h) / 2;
  VkImageBlit blit{};
  blit.srcSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
  blit.dstSubresource = blit.srcSubresource;
  blit.srcOffsets[1] = {int(s.width), int(s.height), 1};
  blit.dstOffsets[0] = {x, y, 0};
  blit.dstOffsets[1] = {x + w, y + h, 1};
  vkCmdBlitImage(s.cmd, t.color.handle, t.color.layout, swap.handle,
                 swap.layout, 1, &blit, VK_FILTER_LINEAR);
  transition(swap, VK_IMAGE_LAYOUT_PRESENT_SRC_KHR);
  VK_CHECK(vkEndCommandBuffer(s.cmd));
  VkPipelineStageFlags stage = VK_PIPELINE_STAGE_TRANSFER_BIT;
  VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};
  si.waitSemaphoreCount = 1;
  si.pWaitSemaphores = &s.acquired;
  si.pWaitDstStageMask = &stage;
  si.commandBufferCount = 1;
  si.pCommandBuffers = &s.cmd;
  si.signalSemaphoreCount = 1;
  si.pSignalSemaphores = &s.finished;
  VK_CHECK(vkQueueSubmit(s.queue, 1, &si, VK_NULL_HANDLE));
  s.recording = false;
  VkPresentInfoKHR pi{VK_STRUCTURE_TYPE_PRESENT_INFO_KHR};
  pi.waitSemaphoreCount = 1;
  pi.pWaitSemaphores = &s.finished;
  pi.swapchainCount = 1;
  pi.pSwapchains = &s.swap;
  pi.pImageIndices = &index;
  result = vkQueuePresentKHR(s.queue, &pi);
  VK_CHECK(vkQueueWaitIdle(s.queue));
  if (result == VK_ERROR_OUT_OF_DATE_KHR || result == VK_SUBOPTIMAL_KHR)
    destroy_swap();
  else
    check(result, "vkQueuePresentKHR");
}
void initialize() {
  s.loader =
      LoadLibraryExW(L"vulkan-1.dll", nullptr, LOAD_LIBRARY_SEARCH_SYSTEM32);
  if (!s.loader)
    throw std::runtime_error(
        "Vulkan loader missing: install the graphics card's Vulkan driver");
  getProc = reinterpret_cast<PFN_vkGetInstanceProcAddr>(
      GetProcAddress(s.loader, "vkGetInstanceProcAddr"));
  if (!getProc)
    throw std::runtime_error("vkGetInstanceProcAddr unavailable");
  auto create = reinterpret_cast<PFN_vkCreateInstance>(
      getProc(VK_NULL_HANDLE, "vkCreateInstance"));
  VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};
  app.pApplicationName = "Renegade Squadron";
  app.apiVersion = VK_API_VERSION_1_1;
  const char *extensions[] = {VK_KHR_SURFACE_EXTENSION_NAME,
                              VK_KHR_WIN32_SURFACE_EXTENSION_NAME};
  VkInstanceCreateInfo ci{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
  ci.pApplicationInfo = &app;
  ci.enabledExtensionCount = 2;
  ci.ppEnabledExtensionNames = extensions;
  VK_CHECK(create(&ci, nullptr, &s.instance));
#define LOAD(name)                                                             \
  vk##name = reinterpret_cast<PFN_vk##name>(getProc(s.instance, "vk" #name));
  VK_FUNCTIONS(LOAD)
#undef LOAD
  unsigned count = 0;
  VK_CHECK(vkEnumeratePhysicalDevices(s.instance, &count, nullptr));
  std::vector<VkPhysicalDevice> gpus(count);
  VK_CHECK(vkEnumeratePhysicalDevices(s.instance, &count, gpus.data()));
  int best = -1;
  for (auto gpu : gpus) {
    VkPhysicalDeviceProperties props;
    vkGetPhysicalDeviceProperties(gpu, &props);
    unsigned n = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(gpu, &n, nullptr);
    std::vector<VkQueueFamilyProperties> families(n);
    vkGetPhysicalDeviceQueueFamilyProperties(gpu, &n, families.data());
    for (unsigned q = 0; q < n; ++q)
      if (families[q].queueFlags & VK_QUEUE_GRAPHICS_BIT) {
        int score =
            props.deviceType == VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU ? 2 : 1;
        if (score > best) {
          best = score;
          s.gpu = gpu;
          s.family = q;
          s.report.message = props.deviceName;
        }
        break;
      }
  }
  if (!s.gpu)
    throw std::runtime_error("No Vulkan graphics queue found");
  vkGetPhysicalDeviceMemoryProperties(s.gpu, &s.memory);
  VkPhysicalDeviceProperties properties{};
  vkGetPhysicalDeviceProperties(s.gpu, &properties);
  unsigned samples = std::min(16u, vcs_configuration().rendering.msaa);
  const auto supported = properties.limits.framebufferColorSampleCounts &
                         properties.limits.framebufferDepthSampleCounts &
                         properties.limits.framebufferStencilSampleCounts;
  while (samples > 1 && !(supported & samples))
    samples >>= 1;
  s.samples = VkSampleCountFlagBits(std::max(1u, samples));
  float priority = 1;
  VkDeviceQueueCreateInfo qi{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
  qi.queueFamilyIndex = s.family;
  qi.queueCount = 1;
  qi.pQueuePriorities = &priority;
  const char *dext = VK_KHR_SWAPCHAIN_EXTENSION_NAME;
  VkDeviceCreateInfo di{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};
  di.queueCreateInfoCount = 1;
  di.pQueueCreateInfos = &qi;
  di.enabledExtensionCount = 1;
  di.ppEnabledExtensionNames = &dext;
  VK_CHECK(vkCreateDevice(s.gpu, &di, nullptr, &s.device));
  vkGetDeviceQueue(s.device, s.family, 0, &s.queue);
  VkCommandPoolCreateInfo cp{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};
  cp.queueFamilyIndex = s.family;
  cp.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
  VK_CHECK(vkCreateCommandPool(s.device, &cp, nullptr, &s.pool));
  VkCommandBufferAllocateInfo ca{
      VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
  ca.commandPool = s.pool;
  ca.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
  ca.commandBufferCount = 1;
  VK_CHECK(vkAllocateCommandBuffers(s.device, &ca, &s.cmd));
  auto dims = resolve_internal_resolution(vcs_configuration().rendering);
  s.width = dims.width;
  s.height = dims.height;
  s.geometry = buffer(32ull * 1024 * 1024, VK_BUFFER_USAGE_VERTEX_BUFFER_BIT);
  s.readback = buffer(VkDeviceSize(s.width) * s.height * 4,
                      VK_BUFFER_USAGE_TRANSFER_DST_BIT);
  VkAttachmentDescription attachments[3]{};
  attachments[0].format = VK_FORMAT_R8G8B8A8_UNORM;
  attachments[1].format = VK_FORMAT_D32_SFLOAT_S8_UINT;
  for (auto &a : attachments) {
    a.samples = s.samples;
    a.loadOp = VK_ATTACHMENT_LOAD_OP_LOAD;
    a.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
    a.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_LOAD;
    a.stencilStoreOp = VK_ATTACHMENT_STORE_OP_STORE;
  }
  attachments[0].initialLayout = attachments[0].finalLayout =
      VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
  attachments[1].initialLayout = attachments[1].finalLayout =
      VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
  attachments[2] = attachments[0];
  attachments[2].samples = VK_SAMPLE_COUNT_1_BIT;
  attachments[2].loadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
  VkAttachmentReference resolve{2, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL};
  VkAttachmentReference color{0, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL},
      depth{1, VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL};
  VkSubpassDescription sub{};
  sub.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
  sub.colorAttachmentCount = 1;
  sub.pColorAttachments = &color;
  sub.pDepthStencilAttachment = &depth;
  if (s.samples != VK_SAMPLE_COUNT_1_BIT)
    sub.pResolveAttachments = &resolve;
  VkRenderPassCreateInfo rp{VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO};
  rp.attachmentCount = s.samples == VK_SAMPLE_COUNT_1_BIT ? 2 : 3;
  rp.pAttachments = attachments;
  rp.subpassCount = 1;
  rp.pSubpasses = &sub;
  VkSubpassDependency dep{};
  dep.srcSubpass = VK_SUBPASS_EXTERNAL;
  dep.dstSubpass = 0;
  dep.srcStageMask = VK_PIPELINE_STAGE_ALL_COMMANDS_BIT;
  dep.dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
                     VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT |
                     VK_PIPELINE_STAGE_LATE_FRAGMENT_TESTS_BIT;
  dep.srcAccessMask = VK_ACCESS_MEMORY_WRITE_BIT;
  dep.dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_READ_BIT |
                      VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT |
                      VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_READ_BIT |
                      VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;
  rp.dependencyCount = 1;
  rp.pDependencies = &dep;
  VK_CHECK(vkCreateRenderPass(s.device, &rp, nullptr, &s.pass));
  VkDescriptorSetLayoutBinding bindings[2] = {
      {0, VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE, 1, VK_SHADER_STAGE_FRAGMENT_BIT,
       nullptr},
      {1, VK_DESCRIPTOR_TYPE_SAMPLER, 1, VK_SHADER_STAGE_FRAGMENT_BIT,
       nullptr}};
  VkDescriptorSetLayoutCreateInfo sl{
      VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
  sl.bindingCount = 2;
  sl.pBindings = bindings;
  VK_CHECK(vkCreateDescriptorSetLayout(s.device, &sl, nullptr, &s.set_layout));
  VkDescriptorPoolSize sizes[] = {{VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE, 16384},
                                  {VK_DESCRIPTOR_TYPE_SAMPLER, 16384}};
  VkDescriptorPoolCreateInfo dp{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
  dp.flags = VK_DESCRIPTOR_POOL_CREATE_FREE_DESCRIPTOR_SET_BIT;
  dp.maxSets = 16384;
  dp.poolSizeCount = 2;
  dp.pPoolSizes = sizes;
  VK_CHECK(vkCreateDescriptorPool(s.device, &dp, nullptr, &s.descriptors));
  VkPushConstantRange pc{VK_SHADER_STAGE_VERTEX_BIT |
                             VK_SHADER_STAGE_FRAGMENT_BIT,
                         0, sizeof(Push)};
  VkPipelineLayoutCreateInfo pl{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
  pl.setLayoutCount = 1;
  pl.pSetLayouts = &s.set_layout;
  pl.pushConstantRangeCount = 1;
  pl.pPushConstantRanges = &pc;
  VK_CHECK(vkCreatePipelineLayout(s.device, &pl, nullptr, &s.layout));
  VkShaderModuleCreateInfo sm{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};
  sm.codeSize = sizeof(vulkan_vertex_spirv);
  sm.pCode = vulkan_vertex_spirv;
  VK_CHECK(vkCreateShaderModule(s.device, &sm, nullptr, &s.vs));
  sm.codeSize = sizeof(vulkan_pixel_spirv);
  sm.pCode = vulkan_pixel_spirv;
  VK_CHECK(vkCreateShaderModule(s.device, &sm, nullptr, &s.ps));
  GeGpuDrawDescriptor white;
  white.texture_clamp_u = white.texture_clamp_v = true;
  upload(s.white, white, 1, 1, 1, std::vector<std::byte>(4, std::byte{255}));
  VkSemaphoreCreateInfo sem{VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO};
  VK_CHECK(vkCreateSemaphore(s.device, &sem, nullptr, &s.acquired));
  VK_CHECK(vkCreateSemaphore(s.device, &sem, nullptr, &s.finished));
  s.enabled = true;
  s.report.active = GeGpuBackendKind::Vulkan;
  s.report.requested = GeGpuBackendKind::Vulkan;
  s.report.loader_opened = s.report.instance_created = s.report.device_created =
      s.report.command_pool_created = true;
  s.report.offscreen_width = s.width;
  s.report.offscreen_height = s.height;
  s.report.physical_device_count = count;
  s.report.graphics_queue_family = s.family;
  s.report.depth_attachment_active = true;
  s.report.alpha_test_shader_active = true;
  s.report.fog_shader_active = true;
  s.report.dx12_msaa_samples = unsigned(s.samples);
  s.report.message += "; native Vulkan, GE vertex lighting";
}
// Snapshot framebuffer feedback before returning to the destination render
// pass. A separate sampled image also handles feedback from the active target
// safely.
Texture &feedback(const GeGpuDrawDescriptor &d) {
  auto &source = s.targets.at(address(d.texture_address));
  auto &t = s.textures[key(d)];
  if (t.image.width != s.width || t.image.height != s.height) {
    submit();
    destroy(t);
    t.image =
        image(s.width, s.height, 1, VK_FORMAT_R8G8B8A8_UNORM,
              VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT,
              VK_IMAGE_ASPECT_COLOR_BIT);
    bind_texture(t, d);
  }
  transition(source.color, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL);
  transition(t.image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL);
  VkImageCopy copy{};
  copy.srcSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
  copy.dstSubresource = copy.srcSubresource;
  copy.extent = {s.width, s.height, 1};
  vkCmdCopyImage(s.cmd, source.color.handle, source.color.layout,
                 t.image.handle, t.image.layout, 1, &copy);
  transition(t.image, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL);
  return t;
}
void draw(const GeGpuDrawDescriptor &d, std::span<const GeGpuVertex> vertices,
          bool clip_space = false) {
  if (!s.enabled || s.failed || vertices.empty())
    return;
  if (vertices.size() % 3)
    throw std::runtime_error("Vulkan triangle list is incomplete");
  auto size = vertices.size_bytes();
  if (size > s.geometry.size)
    throw std::runtime_error("Vulkan draw exceeds vertex buffer capacity");
  if (s.used + size > s.geometry.size) {
    submit();
    s.used = 0;
  }
  Target &t = target(d.framebuffer_address);
  const bool is_feedback =
      vulkan::ge_gpu_backend_is_framebuffer_feedback_texture(d);
  Texture *tex = &s.white;
  if (d.texture_enabled && !d.clear_mode && is_feedback) {
    tex = &feedback(d);
  } else if (d.texture_enabled && !d.clear_mode) {
    auto it = s.textures.find(key(d));
    if (it == s.textures.end())
      throw std::runtime_error("Vulkan textured draw has no decoded texture");
    tex = &it->second;
    tex->last_use = s.frame;
  }
  render(t);
  std::memcpy(static_cast<std::byte *>(s.geometry.mapped) + s.used,
              vertices.data(), size);
  vkCmdBindVertexBuffers(s.cmd, 0, 1, &s.geometry.handle, &s.used);
  s.used += size;
  vkCmdBindPipeline(s.cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline(d));
  VkViewport vp{0, 0, float(s.width), float(s.height), 0, 1};
  vkCmdSetViewport(s.cmd, 0, 1, &vp);
  int x = std::clamp(int(std::floor(d.scissor_x0 * s.width / 480.f)), 0,
                     int(s.width)),
      y = std::clamp(int(std::floor(d.scissor_y0 * s.height / 272.f)), 0,
                     int(s.height));
  int x1 = std::clamp(int(std::ceil((d.scissor_x1 + 1) * s.width / 480.f)), x,
                      int(s.width)),
      y1 = std::clamp(int(std::ceil((d.scissor_y1 + 1) * s.height / 272.f)), y,
                      int(s.height));
  VkRect2D sc{{x, y}, {unsigned(x1 - x), unsigned(y1 - y)}};
  vkCmdSetScissor(s.cmd, 0, 1, &sc);
  float bc[4]{};
  unsigned fix =
      d.blend_source_factor == 10 ? d.blend_fix_source : d.blend_fix_dest;
  for (unsigned c = 0; c < 4; ++c)
    bc[c] = float((fix >> (8 * c)) & 255) / 255;
  vkCmdSetBlendConstants(s.cmd, bc);
  vkCmdSetStencilReference(s.cmd, VK_STENCIL_FACE_FRONT_AND_BACK,
                           d.clear_mode ? (vertices.front().rgba >> 24)
                                        : d.stencil.reference);
  vkCmdBindDescriptorSets(s.cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, s.layout, 0,
                          1, &tex->set, 0, nullptr);
  Push pc{};
  for (unsigned n = 0; n < 4; ++n)
    pc.rows[n][n] = 1;
  if (!clip_space) {
    pc.rows[0] = {2 / 480.f, 0, 0, -1};
    pc.rows[1] = {0, 2 / 272.f, 0, -1};
    pc.rows[2] = {0, 0, 1 / 65535.f, 0};
  }
  pc.uv = {1.f / (is_feedback ? 480u : std::max(1u, d.texture_width)),
           1.f / (is_feedback ? 272u : std::max(1u, d.texture_height)), 0, 0};
  // Hardware-transformed vertices already carry normalized GE texture UVs.
  // Only the screen-space path supplies texel coordinates.
  if (clip_space)
    pc.uv = {1, 1, 0, 0};
  pc.control = {d.clear_mode
                    ? 0u
                    : unsigned(d.alpha_test_enabled) | (d.alpha_function << 8) |
                          (d.alpha_reference << 16) | (d.alpha_mask << 24),
                d.texture_function | (unsigned(d.texture_use_alpha) << 8) |
                    (unsigned(d.texture_double_color) << 16),
                d.fog_color, d.framebuffer_format};
  for (unsigned n = 0; n < 3; ++n)
    pc.fog[n] = float((d.texture_env >> (8 * n)) & 255) / 255;
  pc.flags = {unsigned(d.texture_enabled && !d.clear_mode),
              unsigned(d.fog_enabled && !d.clear_mode), unsigned(s.smooth),
              unsigned(!clip_space)};
  vkCmdPushConstants(s.cmd, s.layout,
                     VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
                     0, sizeof(pc), &pc);
  vkCmdDraw(s.cmd, unsigned(vertices.size()), 1, 0, 0);
  s.owned = address(d.framebuffer_address);
  ++s.report.game_draw_calls;
  s.report.game_triangles += vertices.size() / 3;
  s.report.game_vertices += vertices.size();
}
} // namespace
bool initialize_ge_gpu_backend(std::string &message) {
  shutdown_ge_gpu_backend();
  try {
    initialize();
    message.clear();
    return true;
  } catch (const std::exception &e) {
    message = e.what();
    shutdown_ge_gpu_backend();
    s.report.requested = GeGpuBackendKind::Vulkan;
    s.report.message = message;
    return false;
  }
}
void shutdown_ge_gpu_backend() noexcept {
  if (s.device) {
    vkDeviceWaitIdle(s.device);
    destroy_swap();
    for (auto &[k, p] : s.pipelines)
      vkDestroyPipeline(s.device, p, nullptr);
    for (auto &[k, t] : s.targets) {
      if (t.framebuffer)
        vkDestroyFramebuffer(s.device, t.framebuffer, nullptr);
      destroy(t.color);
      destroy(t.depth);
      destroy(t.multisample);
    }
    for (auto &[k, t] : s.textures)
      destroy(t);
    destroy(s.white);
    destroy(s.geometry);
    destroy(s.readback);
    if (s.acquired)
      vkDestroySemaphore(s.device, s.acquired, nullptr);
    if (s.finished)
      vkDestroySemaphore(s.device, s.finished, nullptr);
    if (s.vs)
      vkDestroyShaderModule(s.device, s.vs, nullptr);
    if (s.ps)
      vkDestroyShaderModule(s.device, s.ps, nullptr);
    if (s.layout)
      vkDestroyPipelineLayout(s.device, s.layout, nullptr);
    if (s.descriptors)
      vkDestroyDescriptorPool(s.device, s.descriptors, nullptr);
    if (s.set_layout)
      vkDestroyDescriptorSetLayout(s.device, s.set_layout, nullptr);
    if (s.pass)
      vkDestroyRenderPass(s.device, s.pass, nullptr);
    if (s.pool)
      vkDestroyCommandPool(s.device, s.pool, nullptr);
    vkDestroyDevice(s.device, nullptr);
  }
  if (s.surface)
    vkDestroySurfaceKHR(s.instance, s.surface, nullptr);
  if (s.instance)
    vkDestroyInstance(s.instance, nullptr);
  if (s.loader)
    FreeLibrary(s.loader);
  s = State{};
}
bool ge_gpu_backend_active() noexcept { return s.enabled && !s.failed; }
bool ge_gpu_backend_transfer_ready() noexcept {
  return ge_gpu_backend_active();
}
bool ge_gpu_backend_graphics_ready() noexcept {
  return ge_gpu_backend_active();
}
void ge_gpu_backend_record_draw(const GeGpuDrawDescriptor &d) noexcept {
  ++s.report.draw_calls;
  s.report.vertices += d.vertex_count;
}
void ge_gpu_backend_observe_camera(const std::array<float, 12> &,
                                   const std::array<float, 16> &,
                                   const std::array<float, 6> &,
                                   const std::array<float, 3> &,
                                   const GeGpuDrawDescriptor &,
                                   std::uint32_t) noexcept {}
bool ge_gpu_backend_stage_vertices(const GeGpuDrawDescriptor &,
                                   std::span<const GeGpuVertex>) noexcept {
  return ge_gpu_backend_active();
}
void ge_gpu_backend_prepare_texture_keys(GeGpuDrawDescriptor &d) noexcept {
  d.texture_cache_key_hint = 0;
  d.texture_cache_key_hint = key(d);
  d.texture_image_key_hint = d.texture_cache_key_hint;
}
bool ge_gpu_backend_texture_needed(const GeGpuDrawDescriptor &d) noexcept {
  if (vulkan::ge_gpu_backend_is_framebuffer_feedback_texture(d))
    return false;
  auto it = s.textures.find(key(d));
  if (it == s.textures.end())
    return true;
  it->second.last_use = s.frame;
  // Zero means the frontend already validated this texture in this frame.
  // It is not a new source checksum and must not trigger an upload.
  return d.texture_content_signature != 0 &&
         it->second.signature != d.texture_content_signature;
}
bool ge_gpu_backend_texture_signature_needed(
    const GeGpuDrawDescriptor &d) noexcept {
  auto it = s.textures.find(key(d));
  return it == s.textures.end() || it->second.last_use != s.frame;
}
bool ge_gpu_backend_is_framebuffer_feedback_texture(
    const GeGpuDrawDescriptor &d) noexcept {
  return !d.texture_replacement &&
         s.targets.contains(address(d.texture_address));
}
GeGpuWidescreenHud
ge_gpu_backend_widescreen_hud(const GeGpuDrawDescriptor &) noexcept {
  return {};
}
void ge_gpu_backend_note_through_extent(const GeGpuDrawDescriptor &, float,
                                        float) noexcept {}
bool ge_gpu_backend_adopt_shared_texture(const GeGpuDrawDescriptor &) noexcept {
  return false;
}
bool ge_gpu_backend_texture_available(const GeGpuDrawDescriptor &d) noexcept {
  return vulkan::ge_gpu_backend_is_framebuffer_feedback_texture(d) ||
         s.textures.contains(key(d));
}
bool ge_gpu_backend_upload_decoded_texture_chain_packed(
    const GeGpuDrawDescriptor &d, std::uint32_t w, std::uint32_t h,
    std::uint32_t levels, std::vector<std::byte> pixels) noexcept {
  try {
    if (!s.enabled || s.failed || !w || !h || w > 16384 || h > 16384 ||
        !levels || levels > 15)
      return false;
    std::size_t expected = 0;
    for (unsigned n = 0; n < levels; ++n)
      expected += std::size_t(std::max(1u, w >> n)) * std::max(1u, h >> n) * 4;
    if (expected != pixels.size())
      return false;
    // Submission retires every descriptor before cache eviction or replacement.
    const auto budget =
        std::size_t(
            std::max(16u, vcs_configuration().rendering.texture_cache_mb)) *
        1024 * 1024;
    std::size_t resident = 0;
    for (const auto &[id, t] : s.textures)
      resident += t.bytes;
    if (resident + pixels.size() > budget || s.textures.size() >= 8192) {
      submit();
      while (!s.textures.empty() &&
             (resident + pixels.size() > budget || s.textures.size() >= 8192)) {
        auto oldest = s.textures.end();
        for (auto it = s.textures.begin(); it != s.textures.end(); ++it)
          if (it->first != key(d) &&
              (oldest == s.textures.end() ||
               it->second.last_use < oldest->second.last_use))
            oldest = it;
        if (oldest == s.textures.end())
          break;
        resident -= oldest->second.bytes;
        destroy(oldest->second);
        s.textures.erase(oldest);
      }
    }
    auto &t = s.textures[key(d)];
    upload(t, d, w, h, levels, std::move(pixels));

    s.report.last_texture_width = w;
    s.report.last_texture_height = h;
    s.report.last_texture_key = key(d);
    return true;
  } catch (const std::exception &e) {
    error(e);
    return false;
  }
}
bool ge_gpu_backend_upload_decoded_texture(
    const GeGpuDrawDescriptor &d, std::uint32_t w, std::uint32_t h,
    std::span<const std::byte> p) noexcept {
  try {
    return vulkan::ge_gpu_backend_upload_decoded_texture_chain_packed(
        d, w, h, 1, {p.begin(), p.end()});
  } catch (const std::exception &e) {
    error(e);
    return false;
  }
}
bool ge_gpu_backend_upload_decoded_texture_chain(
    const GeGpuDrawDescriptor &d,
    std::span<const GeGpuDecodedMipLevel> levels) noexcept {
  try {
    if (levels.empty())
      return false;
    std::vector<std::byte> pixels;
    for (auto &l : levels)
      pixels.insert(pixels.end(), l.rgba8.begin(), l.rgba8.end());
    return vulkan::ge_gpu_backend_upload_decoded_texture_chain_packed(
        d, levels[0].width, levels[0].height, unsigned(levels.size()),
        std::move(pixels));
  } catch (const std::exception &e) {
    error(e);
    return false;
  }
}
bool ge_gpu_backend_copy_last_texture_rgba(std::span<std::byte> dest) noexcept {
  if (dest.size() != s.last_texture.size())
    return false;
  std::copy(s.last_texture.begin(), s.last_texture.end(), dest.begin());
  return true;
}
void ge_gpu_backend_accumulate_color_triangles(
    const GeGpuDrawDescriptor &d, std::span<const GeGpuVertex> v) noexcept {
  try {
    draw(d, v);
  } catch (const std::exception &e) {
    error(e);
  }
}
std::uint32_t ge_gpu_backend_intern_lighting(const GeGpuLighting &) noexcept {
  return 0;
} // GE frontend retains CPU lighting.
std::uint32_t
ge_gpu_backend_intern_palette(std::span<const std::array<float, 4>>) noexcept {
  return 0;
} // GE frontend retains exact CPU palette decode.
bool ge_gpu_backend_attach_normal_map(const GeGpuDrawDescriptor &,
                                      std::uint32_t, std::uint32_t,
                                      std::vector<std::byte>) noexcept {
  return false;
}
void ge_gpu_backend_accumulate_hardware_triangles(
    const GeGpuDrawDescriptor &d, const GeGpuHardwareTransform &t,
    std::span<const GeGpuVertex> vertices,
    std::span<const std::uint32_t> indices) noexcept {
  try {
    std::vector<GeGpuVertex> transformed(vertices.begin(), vertices.end());
    for (auto &v : transformed) {
      float p[] = {v.x, v.y, v.z, v.w}, c[4]{};
      for (unsigned r = 0; r < 4; ++r)
        for (unsigned n = 0; n < 4; ++n)
          c[r] += t.model_to_clip[n * 4 + r] * p[n];
      v.x = (c[0] * t.viewport_scale_x +
             c[3] * (t.viewport_center_x - t.viewport_offset_x)) *
                2 / 480.f -
            c[3];
      v.y = (c[1] * t.viewport_scale_y +
             c[3] * (t.viewport_center_y - t.viewport_offset_y)) *
                2 / 272.f -
            c[3];
      v.z = (c[2] * t.viewport_scale_z + c[3] * t.viewport_center_z) / 65535.f;
      v.w = c[3];
      if (!t.depth_clip_enabled && v.w > 0)
        v.z = std::clamp(v.z, 0.f, v.w);
      float view = 0;
      for (unsigned n = 0; n < 4; ++n)
        view += t.model_to_view_z[n] * p[n];
      v.fog_factor = (view + t.fog_end) * t.fog_slope;
      v.u = v.u * t.uv_scale_u + t.uv_offset_u;
      v.v = v.v * t.uv_scale_v + t.uv_offset_v;
      if (t.vertex_color_affine) {
        unsigned color = 0;
        for (unsigned n = 0; n < 4; ++n) {
          float f = float((v.rgba >> (n * 8)) & 255) / 255;
          auto b = unsigned(
              std::clamp(f * t.vertex_color_mul[n] + t.vertex_color_add[n], 0.f,
                         1.f) *
              255);
          color |= b << (8 * n);
        }
        v.rgba = color;
      }
    }
    std::vector<GeGpuVertex> out;
    auto at = [&](std::size_t n) -> const GeGpuVertex & {
      std::size_t index = indices.empty() ? n : indices[n];
      if (index >= transformed.size())
        throw std::runtime_error("Vulkan index out of range");
      return transformed[index];
    };
    std::size_t count = indices.empty() ? vertices.size() : indices.size();
    auto triangle = [&](std::size_t a, std::size_t b, std::size_t c) {
      auto va = at(a), vb = at(b), vc = at(c);
      if (t.cull_enabled && va.w > 0 && vb.w > 0 && vc.w > 0) {
        float area = (vb.x / vb.w - va.x / va.w) * (vc.y / vc.w - va.y / va.w) -
                     (vb.y / vb.w - va.y / va.w) * (vc.x / vc.w - va.x / va.w);
        if ((area < 0) != t.accept_counter_clockwise)
          return;
      }
      out.push_back(va);
      out.push_back(vb);
      out.push_back(vc);
    };
    if (t.primitive == 4) {
      for (std::size_t n = 2; n < count; ++n)
        triangle(n - 2 + (n & 1), n - 1 - (n & 1), n);
    } else if (t.primitive == 5) {
      for (std::size_t n = 2; n < count; ++n)
        triangle(0, n - 1, n);
    } else {
      for (std::size_t n = 0; n + 2 < count; n += 3)
        triangle(n, n + 1, n + 2);
    }
    draw(d, out, true);
    ++s.report.hw_transform_draw_calls;
  } catch (const std::exception &e) {
    error(e);
  }
}
bool ge_gpu_backend_accumulate_hardware_packed_0115(
    const GeGpuDrawDescriptor &, const GeGpuHardwareTransform &,
    std::span<const std::byte>, std::uint32_t,
    std::span<const std::uint32_t>) noexcept {
  return false;
}
void ge_gpu_backend_set_native_window(void *window) noexcept {
  try {
    submit();
    if (s.device)
      VK_CHECK(vkDeviceWaitIdle(s.device));
    destroy_swap();
    if (s.surface)
      vkDestroySurfaceKHR(s.instance, s.surface, nullptr);
    s.surface = {};
    s.window = static_cast<HWND>(window);
    if (!window || !s.enabled)
      return;
    VkWin32SurfaceCreateInfoKHR ci{
        VK_STRUCTURE_TYPE_WIN32_SURFACE_CREATE_INFO_KHR};
    ci.hinstance = GetModuleHandleW(nullptr);
    ci.hwnd = s.window;
    VK_CHECK(vkCreateWin32SurfaceKHR(s.instance, &ci, nullptr, &s.surface));
    VkBool32 supported = 0;
    VK_CHECK(vkGetPhysicalDeviceSurfaceSupportKHR(s.gpu, s.family, s.surface,
                                                  &supported));
    if (!supported)
      throw std::runtime_error(
          "Vulkan graphics queue cannot present to this window");
    ensure_swap();
  } catch (const std::exception &e) {
    error(e);
  }
}
void ge_gpu_backend_set_display_framebuffer(std::uint32_t a) noexcept {
  s.display = address(a);
}
bool ge_gpu_backend_finish_color_frame(std::uint64_t vblank) noexcept {
  try {
    if (!s.enabled || s.failed || s.targets.empty())
      return false;
    auto it = s.targets.find(s.display);
    if (it == s.targets.end())
      it = s.targets.find(s.owned);
    if (it == s.targets.end())
      return false;
    auto &t = it->second;
    transition(t.color, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL);
    VkBufferImageCopy copy{};
    copy.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
    copy.imageExtent = {s.width, s.height, 1};
    vkCmdCopyImageToBuffer(s.cmd, t.color.handle, t.color.layout,
                           s.readback.handle, 1, &copy);
    submit();
    s.pixels.resize(std::size_t(s.width) * s.height * 4);
    std::memcpy(s.pixels.data(), s.readback.mapped, s.pixels.size());
    if (s.window)
      present(t);
    s.used = 0;
    s.frame++;
    s.report.game_frames++;
    s.report.game_frame_vblank = vblank;
    s.report.game_frame_readback_bytes = s.pixels.size();
    return true;
  } catch (const std::exception &e) {
    error(e);
    return false;
  }
}
bool ge_gpu_backend_copy_game_frame_rgba(std::span<std::byte> dest) noexcept {
  if (dest.size() != s.pixels.size())
    return false;
  std::copy(s.pixels.begin(), s.pixels.end(), dest.begin());
  return true;
}
bool ge_gpu_backend_presents_directly() noexcept {
  return s.enabled && !s.failed && s.window && s.surface;
}
bool ge_gpu_backend_presented_rectangle(std::uint32_t w, std::uint32_t h,
                                        std::int32_t &x, std::int32_t &y,
                                        std::int32_t &rw,
                                        std::int32_t &rh) noexcept {
  if (!ge_gpu_backend_presents_directly())
    return false;
  float scale = std::min(float(w) / s.width, float(h) / s.height);
  rw = int(s.width * scale);
  rh = int(s.height * scale);
  x = (int(w) - rw) / 2;
  y = (int(h) - rh) / 2;
  return true;
}
std::uint32_t ge_gpu_backend_owned_framebuffer() noexcept {
  return s.enabled ? s.owned : 0;
}
std::uint32_t ge_gpu_backend_display_framebuffer() noexcept {
  return s.enabled ? s.display : 0;
}
std::span<const std::byte> ge_gpu_backend_game_frame_rgba() noexcept {
  return s.pixels;
}
bool ge_gpu_backend_copy_offscreen_rgba(std::span<std::byte> d) noexcept {
  return ge_gpu_backend_copy_game_frame_rgba(d);
}
void ge_gpu_backend_mark_window_presented() noexcept {}
GeGpuBackendReport ge_gpu_backend_report() { return s.report; }
void ge_gpu_backend_set_shadows(bool) noexcept {}
void ge_gpu_backend_set_bloom(bool) noexcept {}
void ge_gpu_backend_set_smooth_fog(bool enabled) noexcept {
  s.smooth = enabled;
}
const char *ge_gpu_backend_name(GeGpuBackendKind kind) noexcept {
  return kind == GeGpuBackendKind::Vulkan      ? "Vulkan"
         : kind == GeGpuBackendKind::DirectX12 ? "DirectX 12"
                                               : "Software";
}
} // namespace vcs::vulkan
