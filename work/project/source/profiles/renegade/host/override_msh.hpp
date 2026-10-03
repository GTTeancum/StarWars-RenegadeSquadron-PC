#pragma once
#include <array>
#include <cstdint>
#include <filesystem>
#include <span>
#include <string>
#include <vector>

namespace renegade::overrides {
struct MshMaterial {
    std::string name;
    std::array<std::string,4> textures;
    std::array<std::uint8_t,4> attributes{};
    // DATA is 13 little-endian floats: diffuse, specular, ambient RGBA,
    // then exponent. Keep raw finite values; rendering chooses semantics.
    std::array<float,4> diffuse{1,1,1,1}, specular{1,1,1,1}, ambient{1,1,1,1};
    float specular_exponent{50};
    bool has_data{};
};
struct MshWeight { std::uint32_t bone{}; float weight{}; };
struct MshSegment {
    std::uint32_t material{};
    std::vector<std::array<float,3>> positions, normals;
    std::vector<std::array<float,2>> uv;
    std::vector<std::uint32_t> colors;
    std::vector<std::array<MshWeight,4>> weights;
    std::vector<std::array<std::uint32_t,3>> triangles;
};
struct MshNode {
    std::string name, parent;
    std::uint32_t index{}, type{}, flags{};
    std::array<float,3> scale{1,1,1}, translation{};
    std::array<float,4> rotation{0,0,0,1}; // quaternion xyzw, original MSH coordinates
    std::vector<std::uint32_t> envelope;
    std::vector<MshSegment> segments;
};
struct MshScene {
    std::vector<MshMaterial> materials;
    std::vector<MshNode> nodes;
    // Explicitly retained so rendering cannot silently claim unsupported features.
    bool has_animation{}, has_cloth{}, has_shadow_volumes{};
};
// Strict little-endian HEDR/MSH2 parser. Unknown chunks are skipped by size.
// No file reads are performed for material texture names. Failure preserves output.
bool parse_msh(std::span<const std::uint8_t>, MshScene&, std::string& error);
bool load_msh(const std::filesystem::path&, MshScene&, std::string& error);
}
