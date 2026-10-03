#pragma once
#include "override_model.hpp"
#include <map>
namespace renegade::overrides {
struct WorldVertexBinding {std::array<float,3> source,guest;};
struct WorldMatchStats {std::uint64_t attempted_draws{},matched_draws{},matched_triangles{},ambiguous_draws{};std::map<std::string,std::uint64_t> material_triangles;};
// Matches authored triangles to the unchanged game's static world positions.
// Texture pixels and authored UVs are never transformed.
class WorldGeometry {
    struct Triangle {ModelSegment material;std::array<ModelVertex,3> vertices;std::array<std::array<float,3>,3> match_positions;};
    using Cell=std::array<int,3>;
    std::map<Cell,std::vector<Triangle>> cells_;
    mutable WorldMatchStats stats_;
public:
    void add(const Model&,const std::array<float,3>& scale,const std::array<float,3>& translation={},const std::vector<WorldVertexBinding>& bindings={});
    std::shared_ptr<const Model> match_strip(const std::vector<std::array<float,3>>&) const;
    WorldMatchStats take_stats() const noexcept {auto result=std::move(stats_);stats_={};return result;}
};
const WorldGeometry* configured_world() noexcept;
}
