#pragma once
#include "override_model.hpp"
#include "override_pose.hpp"

namespace renegade::overrides {
struct SkinBinding {
    std::uint32_t msh_index{},pose_slot{};
    // Explicit conversion from compiled MSH model coordinates into the target
    // bone's local coordinates. The adapter supplies bind/axis/scale conversion.
    PoseMatrix model_to_bone{};
};
struct SkinInfluence {std::uint32_t binding{};float weight{};};
struct SkinModel {
    Model bind_model;
    std::vector<SkinBinding> bindings;
    std::vector<std::vector<std::array<SkinInfluence,4>>> influences;
};
// Resolve ENVL/WGHT through explicit bindings. Both functions preserve output
// on failure. Results retain segment materials, UVs, colors and shared textures.
// Motion comes only from PoseSnapshot; embedded MSH animation clips are unused.
bool compile_skin(const MshScene&,std::span<const SkinBinding>,SkinModel&,std::string&);
bool deform_skin(const SkinModel&,const PoseSnapshot&,Model&,std::string&);
// Use the camera-composed matrices already associated with the original GE draw.
// The renderer must use an identity world matrix for this result.
bool deform_skin_camera(const SkinModel&,const PoseSnapshot&,Model&,std::string&);
// Versioned text: RS_SKIN_BINDINGS 1, count, then count records consisting of
// MSH model index, target pose slot, and 16 column-major correction floats.
// No comments or trailing tokens. Both loaders preserve output on failure.
bool load_skin_bindings(const std::filesystem::path&,std::vector<SkinBinding>&,std::string&);
bool load_skin(const std::filesystem::path& msh,const std::filesystem::path& bindings,
               SkinModel&,std::string&);
// Cached whole-character candidate at models/<resource>/model.msh with
// model.bindings alongside it. Invalid/absent candidates return null.
std::shared_ptr<const SkinModel> find_skin_model(const std::string& resource) noexcept;
}
