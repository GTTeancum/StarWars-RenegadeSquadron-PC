#pragma once
#include "ge_gpu_backend.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>

namespace renegade::movie105 {
// The decoder writes a completed picture directly into RAM. Submit that
// picture after GE draws so a stale clear cannot replace it with black. This
// owns a host-only texture identity, not a guest texture or override binding.
inline bool queue_picture(std::uint32_t framebuffer, std::uint32_t width,
                          std::uint32_t height, std::span<const std::byte> rgba) {
    if (!vcs::ge_gpu_backend_active() || !width || !height || width>16384 || height>16384 ||
        std::uint64_t(width)*height*4u!=rgba.size()) return false;
    const auto report=vcs::ge_gpu_backend_report();
    if (!report.offscreen_width || !report.offscreen_height) return false;
    vcs::GeGpuDrawDescriptor draw{};
    draw.framebuffer_address=framebuffer;draw.framebuffer_stride=512;draw.framebuffer_format=3;
    draw.primitive=3;draw.vertex_count=6;draw.through=true;
    draw.texture_enabled=true;draw.texture_replacement=true;
    draw.texture_address=0x0FFF0105u; // outside PSP RAM/VRAM, never read as guest memory
    draw.texture_cache_key_hint=draw.texture_image_key_hint=0x4D4F564945010500ull;
    draw.texture_width=width;draw.texture_height=height;draw.texture_buffer_width=width;
    draw.texture_format=3;draw.texture_function=3; // replace RGB, opaque presentation
    draw.texture_clamp_u=draw.texture_clamp_v=true;
    if (!vcs::ge_gpu_backend_upload_decoded_texture(draw,width,height,rgba)) return false;
    vcs::ge_gpu_backend_record_draw(draw);
    auto rectangle=[](float x,float y,float w,float h,float u,float v,std::uint32_t color) {
        std::array<vcs::GeGpuVertex,6> vertices{};
        const std::array<std::array<float,4>,6> corners{{{x,y,0,0},{x+w,y,u,0},{x,y+h,0,v},
                                                        {x+w,y,u,0},{x+w,y+h,u,v},{x,y+h,0,v}}};
        for(unsigned i=0;i<6;++i) {
            vertices[i].x=corners[i][0];vertices[i].y=corners[i][1];
            vertices[i].u=corners[i][2];vertices[i].v=corners[i][3];vertices[i].rgba=color;
            vertices[i].texture_control=3u; // same REPLACE mode in the fragment stage
        }
        return vertices;
    };
    auto background=draw;background.texture_enabled=false;
    vcs::ge_gpu_backend_accumulate_color_triangles(background,rectangle(0,0,480,272,0,0,0xFF000000u));
    // Keep the decoded picture's aspect in the actual target. Coordinates are
    // expressed back in reference space; no source pixels/channels are changed.
    const float scale=std::min(float(report.offscreen_width)/width,float(report.offscreen_height)/height);
    const float w=width*scale*480/report.offscreen_width;
    const float h=height*scale*272/report.offscreen_height;
    vcs::ge_gpu_backend_accumulate_color_triangles(draw,
        rectangle((480-w)/2,(272-h)/2,w,h,float(width),float(height),0xFFFFFFFFu));
    return true;
}
} // namespace renegade::movie105
