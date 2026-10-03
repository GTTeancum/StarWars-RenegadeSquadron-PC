#pragma once
#include "override_msh.hpp"
#include "override_texture.hpp"
#include "psprecomp/guest_memory.hpp"
#include <memory>
namespace renegade::overrides {
struct ModelVertex {
    std::array<float,3> position,normal;
    std::array<float,2> uv;
    std::uint32_t color{0xffffffff}; // classic MSH ARGB
    bool has_color{};
};
struct ModelSegment {
    std::vector<ModelVertex> vertices; // triangle list
    std::shared_ptr<Texture> texture;
    std::string texture_name;
    std::uint8_t material_flags{};
    bool gloss{};
    std::array<float,3> specular{1,1,1};
    bool per_pixel{};
    std::string normal_texture_name;
    std::shared_ptr<Texture> normal_texture;
    bool normal_is_height{};
    bool normal_image_missing{};
    float bump_scale{1};
    float specular_exponent{50};
};
struct Model {
    std::vector<ModelSegment> segments;std::string source_path;
    std::size_t derived_normal_vertices{},degenerate_triangles{};
};
bool compile_model(const MshScene&,Model&,std::string& error);
// Loads geometry and every referenced diffuse image atomically. Missing or
// invalid images reject the override; the caller can retain original geometry.
bool load_model(const std::filesystem::path&,Model&,std::string& error);
// Resolve all diffuse images beside path. Preserves model on any failure.
bool load_model_materials(const std::filesystem::path&,Model&,std::string& error);
std::shared_ptr<const Model> find_model_part(const psprecomp::GuestMemory&,
    std::uint32_t vertex_address,std::uint32_t index_address,std::uint32_t primitive) noexcept;
}
