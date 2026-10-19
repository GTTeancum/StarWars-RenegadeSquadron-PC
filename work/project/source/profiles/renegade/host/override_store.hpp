#pragma once
#include "override_texture.hpp"
#include <memory>
#include <span>
namespace renegade::overrides {
bool textures_enabled() noexcept;
// Provenance only: addresses never participate in the content-based override ID.
struct TextureSource {
    std::uint32_t address{}, format{}, buffer_width{}, mip_level{}, clut_address{};
    bool swizzled{};
    // Raw palette-index pixels of an IDX4/IDX8 texture as stored (swizzled), for
    // the palette-independent name match; the game recolours unit palettes.
    const std::uint8_t* indices{};
    std::size_t index_bytes{};
};
std::string texture_id(std::uint32_t width,std::uint32_t height,std::span<const std::uint8_t> rgba);
// Call on the guest rendering thread. Shared ownership keeps active draws valid.
std::shared_ptr<const Texture> find_texture(std::uint32_t width,std::uint32_t height,
                                          std::span<const std::uint8_t> rgba,
                                          const TextureSource* source=nullptr) noexcept;
}
