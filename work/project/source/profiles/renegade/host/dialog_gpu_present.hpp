#pragma once
#include "ge_gpu_backend.hpp"
#include <array>
#include <cstddef>
#include <span>

namespace renegade::dialog {
// Composites a host-drawn RGBA overlay (the PSP system message) over the whole
// 480x272 reference frame with standard alpha blending, after the game's own
// draws. Same host-only texture approach as movie105::queue_picture.
inline bool queue_overlay(std::uint32_t framebuffer, std::uint32_t width, std::uint32_t height,
                          std::span<const std::byte> rgba) {
    if (!vcs::ge_gpu_backend_active() || !width || !height ||
        std::uint64_t(width) * height * 4u != rgba.size()) return false;
    vcs::GeGpuDrawDescriptor draw{};
    draw.framebuffer_address = framebuffer; draw.framebuffer_stride = 512; draw.framebuffer_format = 3;
    draw.primitive = 3; draw.vertex_count = 6; draw.through = true;
    draw.texture_enabled = true; draw.texture_replacement = true;
    draw.texture_address = 0x0FFF0D1Au;  // outside PSP RAM/VRAM, never read as guest memory
    draw.texture_cache_key_hint = draw.texture_image_key_hint = 0x4449414C4F470001ull;
    draw.texture_width = width; draw.texture_height = height; draw.texture_buffer_width = width;
    draw.texture_format = 3; draw.texture_function = 3; draw.texture_use_alpha = true;
    draw.texture_clamp_u = draw.texture_clamp_v = true;
    draw.texture_min_linear = draw.texture_mag_linear = draw.texture_linear = true;
    draw.blend_enabled = true; draw.blend_equation = 0; draw.blend_source_factor = 2; draw.blend_dest_factor = 3;
    if (!vcs::ge_gpu_backend_upload_decoded_texture(draw, width, height, rgba)) return false;
    vcs::ge_gpu_backend_record_draw(draw);
    std::array<vcs::GeGpuVertex, 6> vertices{};
    const std::array<std::array<float, 4>, 6> corners{{{0, 0, 0, 0}, {480, 0, float(width), 0},
                                                      {0, 272, 0, float(height)}, {480, 0, float(width), 0},
                                                      {480, 272, float(width), float(height)}, {0, 272, 0, float(height)}}};
    for (unsigned i = 0; i < 6; ++i) {
        vertices[i].x = corners[i][0]; vertices[i].y = corners[i][1];
        vertices[i].u = corners[i][2]; vertices[i].v = corners[i][3];
        vertices[i].rgba = 0xFFFFFFFFu;
        vertices[i].texture_control = 3u | (1u << 8u);  // REPLACE, use texture alpha
    }
    vcs::ge_gpu_backend_accumulate_color_triangles(draw, vertices);
    return true;
}
} // namespace renegade::dialog
