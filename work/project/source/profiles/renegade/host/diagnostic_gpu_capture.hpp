#pragma once
#include "ge_gpu_backend.hpp"
#include "ge_renderer.hpp"
#include <filesystem>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <string>

namespace renegade::diagnostic104 {
struct GpuCapture {
    bool captured{};
    std::uint64_t source_vblank{};
    std::uint32_t width{}, height{};
    std::string frame, fxaa_frame;
};

// Only a freshly finished readback qualifies. A held GPU image must never be
// labeled as the current controller boundary; retain the native reference.
inline GpuCapture capture_gpu_frame(const std::filesystem::path& directory,
                                    const std::string& stem,
                                    std::uint64_t vblank, std::uint32_t framebuffer,
                                    const vcs::GeGpuBackendReport& report,
                                    std::span<const std::byte> rgba, bool fxaa) {
    GpuCapture result;
    result.source_vblank=report.game_frame_vblank;
    if (!vblank || report.game_frame_vblank!=vblank || rgba.empty() ||
        !report.offscreen_width || !report.offscreen_height) return result;
    const std::uint64_t bytes=std::uint64_t(report.offscreen_width)*report.offscreen_height*4u;
    if (bytes>std::numeric_limits<std::size_t>::max() || rgba.size()!=bytes)
        throw std::runtime_error("Incomplete controller GPU readback");
    const std::filesystem::path leaf(stem);
    if (leaf.empty() || leaf.has_parent_path() || leaf=="." || leaf=="..")
        throw std::runtime_error("Invalid controller capture basename");
    const auto write=[&](const std::string& filename, std::span<const std::byte> pixels) {
        std::ofstream output(directory/filename,std::ios::binary);
        output<<"P6\n"<<report.offscreen_width<<' '<<report.offscreen_height<<"\n255\n";
        for (std::size_t offset=0;offset<pixels.size();offset+=4u) {
            const char rgb[]{char(pixels[offset]),char(pixels[offset+1]),char(pixels[offset+2])};
            output.write(rgb,3);
        }
        output.close();
        if (!output) throw std::runtime_error("Cannot save controller GPU capture");
    };
    result.frame=stem+"-gpu.ppm";
    write(result.frame,rgba);
    if (fxaa) {
        const auto filtered=vcs::ge_fxaa_gpu_rgba(framebuffer,report.offscreen_width,report.offscreen_height,rgba);
        result.fxaa_frame=stem+"-gpu-fxaa.ppm";
        write(result.fxaa_frame,filtered);
    }
    result.width=report.offscreen_width;
    result.height=report.offscreen_height;
    result.captured=true;
    return result;
}
} // namespace renegade::diagnostic104
