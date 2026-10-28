#include "ge_gpu_backend.hpp"
#include "vcs_config.hpp"
#include <utility>
namespace vcs {
namespace dx12 {
const char *ge_gpu_backend_name(GeGpuBackendKind) noexcept;
#include "ge_gpu_backend_api.inc"
} // namespace dx12
namespace vulkan {
#include "ge_gpu_backend_api.inc"
}
const char *ge_gpu_backend_name(GeGpuBackendKind kind) noexcept {
  return kind == GeGpuBackendKind::Vulkan ? "Vulkan"
                                          : dx12::ge_gpu_backend_name(kind);
}
namespace {
bool selected_vulkan = false;
}
bool initialize_ge_gpu_backend(std::string &error) {
  shutdown_ge_gpu_backend();
  selected_vulkan =
      vcs_configuration().rendering.backend == RenderingBackend::Vulkan;
  return selected_vulkan ? vulkan::initialize_ge_gpu_backend(error)
                         : dx12::initialize_ge_gpu_backend(error);
}
void shutdown_ge_gpu_backend() noexcept {
  if (selected_vulkan)
    return vulkan::shutdown_ge_gpu_backend();
  return dx12::shutdown_ge_gpu_backend();
}
bool ge_gpu_backend_active() noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_active();
  return dx12::ge_gpu_backend_active();
}
bool ge_gpu_backend_transfer_ready() noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_transfer_ready();
  return dx12::ge_gpu_backend_transfer_ready();
}
bool ge_gpu_backend_graphics_ready() noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_graphics_ready();
  return dx12::ge_gpu_backend_graphics_ready();
}
void ge_gpu_backend_record_draw(const GeGpuDrawDescriptor &draw) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_record_draw(draw);
  return dx12::ge_gpu_backend_record_draw(draw);
}
void ge_gpu_backend_observe_camera(const std::array<float, 12> &view,
                                   const std::array<float, 16> &projection,
                                   const std::array<float, 6> &viewport,
                                   const std::array<float, 3> &camera_position,
                                   const GeGpuDrawDescriptor &draw,
                                   std::uint32_t vertex_weight) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_observe_camera(
        view, projection, viewport, camera_position, draw, vertex_weight);
  return dx12::ge_gpu_backend_observe_camera(
      view, projection, viewport, camera_position, draw, vertex_weight);
}
bool ge_gpu_backend_stage_vertices(
    const GeGpuDrawDescriptor &draw,
    std::span<const GeGpuVertex> vertices) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_stage_vertices(draw, vertices);
  return dx12::ge_gpu_backend_stage_vertices(draw, vertices);
}
bool ge_gpu_backend_texture_needed(const GeGpuDrawDescriptor &draw) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_texture_needed(draw);
  return dx12::ge_gpu_backend_texture_needed(draw);
}
void ge_gpu_backend_prepare_texture_keys(GeGpuDrawDescriptor &draw) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_prepare_texture_keys(draw);
  return dx12::ge_gpu_backend_prepare_texture_keys(draw);
}
bool ge_gpu_backend_texture_signature_needed(
    const GeGpuDrawDescriptor &draw) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_texture_signature_needed(draw);
  return dx12::ge_gpu_backend_texture_signature_needed(draw);
}
bool ge_gpu_backend_is_framebuffer_feedback_texture(
    const GeGpuDrawDescriptor &draw) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_is_framebuffer_feedback_texture(draw);
  return dx12::ge_gpu_backend_is_framebuffer_feedback_texture(draw);
}
GeGpuWidescreenHud
ge_gpu_backend_widescreen_hud(const GeGpuDrawDescriptor &draw) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_widescreen_hud(draw);
  return dx12::ge_gpu_backend_widescreen_hud(draw);
}
void ge_gpu_backend_note_through_extent(const GeGpuDrawDescriptor &draw,
                                        float max_x, float max_y) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_note_through_extent(draw, max_x, max_y);
  return dx12::ge_gpu_backend_note_through_extent(draw, max_x, max_y);
}
bool ge_gpu_backend_adopt_shared_texture(
    const GeGpuDrawDescriptor &draw) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_adopt_shared_texture(draw);
  return dx12::ge_gpu_backend_adopt_shared_texture(draw);
}
bool ge_gpu_backend_texture_available(
    const GeGpuDrawDescriptor &draw) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_texture_available(draw);
  return dx12::ge_gpu_backend_texture_available(draw);
}
bool ge_gpu_backend_upload_decoded_texture(
    const GeGpuDrawDescriptor &draw, std::uint32_t width, std::uint32_t height,
    std::span<const std::byte> rgba8) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_upload_decoded_texture(draw, width, height,
                                                         rgba8);
  return dx12::ge_gpu_backend_upload_decoded_texture(draw, width, height,
                                                     rgba8);
}
bool ge_gpu_backend_upload_decoded_texture_chain(
    const GeGpuDrawDescriptor &draw,
    std::span<const GeGpuDecodedMipLevel> levels) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_upload_decoded_texture_chain(draw, levels);
  return dx12::ge_gpu_backend_upload_decoded_texture_chain(draw, levels);
}
bool ge_gpu_backend_upload_decoded_texture_chain_packed(
    const GeGpuDrawDescriptor &draw, std::uint32_t base_width,
    std::uint32_t base_height, std::uint32_t mip_levels,
    std::vector<std::byte> rgba8) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_upload_decoded_texture_chain_packed(
        draw, base_width, base_height, mip_levels, std::move(rgba8));
  return dx12::ge_gpu_backend_upload_decoded_texture_chain_packed(
      draw, base_width, base_height, mip_levels, std::move(rgba8));
}
bool ge_gpu_backend_copy_last_texture_rgba(
    std::span<std::byte> destination) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_copy_last_texture_rgba(destination);
  return dx12::ge_gpu_backend_copy_last_texture_rgba(destination);
}
void ge_gpu_backend_accumulate_color_triangles(
    const GeGpuDrawDescriptor &draw,
    std::span<const GeGpuVertex> triangle_vertices) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_accumulate_color_triangles(draw,
                                                             triangle_vertices);
  return dx12::ge_gpu_backend_accumulate_color_triangles(draw,
                                                         triangle_vertices);
}
std::uint32_t
ge_gpu_backend_intern_lighting(const GeGpuLighting &lighting) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_intern_lighting(lighting);
  return dx12::ge_gpu_backend_intern_lighting(lighting);
}
std::uint32_t ge_gpu_backend_intern_palette(
    std::span<const std::array<float, 4>> entries) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_intern_palette(entries);
  return dx12::ge_gpu_backend_intern_palette(entries);
}
bool ge_gpu_backend_attach_normal_map(const GeGpuDrawDescriptor &draw,
                                      std::uint32_t width, std::uint32_t height,
                                      std::vector<std::byte> rgba) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_attach_normal_map(draw, width, height,
                                                    std::move(rgba));
  return dx12::ge_gpu_backend_attach_normal_map(draw, width, height,
                                                std::move(rgba));
}
void ge_gpu_backend_accumulate_hardware_triangles(
    const GeGpuDrawDescriptor &draw, const GeGpuHardwareTransform &transform,
    std::span<const GeGpuVertex> vertices,
    std::span<const std::uint32_t> triangle_indices) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_accumulate_hardware_triangles(
        draw, transform, vertices, triangle_indices);
  return dx12::ge_gpu_backend_accumulate_hardware_triangles(
      draw, transform, vertices, triangle_indices);
}
bool ge_gpu_backend_accumulate_hardware_packed_0115(
    const GeGpuDrawDescriptor &draw, const GeGpuHardwareTransform &transform,
    std::span<const std::byte> packed_vertices, std::uint32_t vertex_count,
    std::span<const std::uint32_t> triangle_indices) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_accumulate_hardware_packed_0115(
        draw, transform, packed_vertices, vertex_count, triangle_indices);
  return dx12::ge_gpu_backend_accumulate_hardware_packed_0115(
      draw, transform, packed_vertices, vertex_count, triangle_indices);
}
void ge_gpu_backend_set_native_window(void *native_window) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_set_native_window(native_window);
  return dx12::ge_gpu_backend_set_native_window(native_window);
}
void ge_gpu_backend_set_display_framebuffer(std::uint32_t address) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_set_display_framebuffer(address);
  return dx12::ge_gpu_backend_set_display_framebuffer(address);
}
bool ge_gpu_backend_finish_color_frame(std::uint64_t vblank) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_finish_color_frame(vblank);
  return dx12::ge_gpu_backend_finish_color_frame(vblank);
}
bool ge_gpu_backend_copy_game_frame_rgba(
    std::span<std::byte> destination) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_copy_game_frame_rgba(destination);
  return dx12::ge_gpu_backend_copy_game_frame_rgba(destination);
}
bool ge_gpu_backend_presents_directly() noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_presents_directly();
  return dx12::ge_gpu_backend_presents_directly();
}
bool ge_gpu_backend_presented_rectangle(std::uint32_t client_width,
                                        std::uint32_t client_height,
                                        std::int32_t &x, std::int32_t &y,
                                        std::int32_t &width,
                                        std::int32_t &height) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_presented_rectangle(
        client_width, client_height, x, y, width, height);
  return dx12::ge_gpu_backend_presented_rectangle(client_width, client_height,
                                                  x, y, width, height);
}
std::uint32_t ge_gpu_backend_owned_framebuffer() noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_owned_framebuffer();
  return dx12::ge_gpu_backend_owned_framebuffer();
}
std::uint32_t ge_gpu_backend_display_framebuffer() noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_display_framebuffer();
  return dx12::ge_gpu_backend_display_framebuffer();
}
std::span<const std::byte> ge_gpu_backend_game_frame_rgba() noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_game_frame_rgba();
  return dx12::ge_gpu_backend_game_frame_rgba();
}
bool ge_gpu_backend_copy_offscreen_rgba(
    std::span<std::byte> destination) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_copy_offscreen_rgba(destination);
  return dx12::ge_gpu_backend_copy_offscreen_rgba(destination);
}
void ge_gpu_backend_mark_window_presented() noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_mark_window_presented();
  return dx12::ge_gpu_backend_mark_window_presented();
}
GeGpuBackendReport ge_gpu_backend_report() {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_report();
  return dx12::ge_gpu_backend_report();
}
void ge_gpu_backend_set_shadows(bool enabled) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_set_shadows(enabled);
  return dx12::ge_gpu_backend_set_shadows(enabled);
}
void ge_gpu_backend_set_bloom(bool enabled) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_set_bloom(enabled);
  return dx12::ge_gpu_backend_set_bloom(enabled);
}
void ge_gpu_backend_set_smooth_fog(bool enabled) noexcept {
  if (selected_vulkan)
    return vulkan::ge_gpu_backend_set_smooth_fog(enabled);
  return dx12::ge_gpu_backend_set_smooth_fog(enabled);
}
} // namespace vcs
