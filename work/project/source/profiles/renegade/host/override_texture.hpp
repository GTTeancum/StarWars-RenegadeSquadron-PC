#pragma once
#include <cstdint>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

namespace renegade::overrides {
// Top-down, tightly packed RGBA8; no guest-memory ownership.
struct Texture {
    std::uint32_t width{}, height{};
    std::vector<std::uint8_t> rgba;
    // Global texture policy only; mesh-bound images retain their own alpha.
    bool use_original_alpha{};
    // Optional tangent-space normal map (textures/<id>_n.*), RGB = XYZ * 0.5 + 0.5.
    std::shared_ptr<const Texture> normal_map;
};
// Failure leaves output unchanged so callers can retain the original texture.
bool load_texture(const std::filesystem::path&, Texture&, std::string& error);
}
