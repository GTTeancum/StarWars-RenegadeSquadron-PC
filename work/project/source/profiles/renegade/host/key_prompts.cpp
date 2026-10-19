// Keyboard/mouse button prompts; see key_prompts.hpp.
#include "key_prompts.hpp"
#include "game_font.hpp"
#include "modern_input008.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <vector>

namespace renegade::key_prompts {
using overrides::Texture;
namespace {
struct Region { float u0, v0, u1, v1; };

// GRAPHICS\PSPBUTTONS.ASR TTXT table: for every region, four floats (u0 v0 u1 v1)
// followed by the region's name ("button_x.tga"), padded to four bytes.
// Same reading as work\tools\pcmods\build_button_atlas.py.
std::map<std::string, Region> load_regions(const std::filesystem::path &asr) {
    std::map<std::string, Region> out;
    std::ifstream in(asr, std::ios::binary);
    if (!in) return out;
    const std::vector<char> b((std::istreambuf_iterator<char>(in)), {});
    const char tag[] = "TTXT";
    const auto it = std::search(b.begin(), b.end(), tag, tag + 4);
    if (it == b.end()) return out;
    const std::size_t j = static_cast<std::size_t>(it - b.begin());
    std::uint32_t size = 0;
    std::memcpy(&size, b.data() + j + 4, 4);
    const std::size_t end = std::min(b.size(), j + size);
    std::size_t p = j + 20;
    const auto printable = [&](std::size_t q) { return q < end && b[q] >= 0x20 && b[q] < 0x7f; };
    std::vector<std::pair<std::string, std::vector<float>>> items;
    while (p < end) {
        std::size_t q = p;
        while (q < end && b[q] != 0) ++q;
        std::string name(b.data() + p, b.data() + q);
        ++q;
        while (q % 4) ++q;
        std::vector<float> floats;
        while (q + 4 <= end && !(printable(q) && printable(q + 1) && printable(q + 2))) {
            float f;
            std::memcpy(&f, b.data() + q, 4);
            floats.push_back(f);
            q += 4;
        }
        items.emplace_back(std::move(name), std::move(floats));
        p = q;
    }
    for (std::size_t k = 0; k + 1 < items.size(); ++k) {
        const auto &f = items[k].second;
        if (f.size() < 4) continue;
        std::string name = items[k + 1].first;
        if (const auto dot = name.rfind(".tga"); dot != std::string::npos) name.resize(dot);
        out[name] = Region{f[0], f[1], f[2], f[3]};
    }
    return out;
}

// What each prompt glyph stands for, as the Xbox pack maps them
// (build_button_atlas.py): the binding whose key it names.
const char *binding_for(const std::string &glyph) {
    static const std::map<std::string, const char *> table{
        {"big_x", "A"}, {"button_x", "A"}, {"big_circle", "B"}, {"button_circle", "B"},
        {"big_square", "X"}, {"button_square", "X"}, {"big_triangle", "Y"}, {"button_triangle", "Y"},
        {"button_l1", "LB"}, {"button_r1", "RB"}, {"button_select", "Back"}, {"button_start", "Start"},
        // HUD prompt: change equipment / use (X in the PC layout).
        {"d_pad_up_Small", "X"}, {"d_pad_dn_Small", "Down"},
    };
    const auto it = table.find(glyph);
    return it == table.end() ? nullptr : it->second;
}
// Menu-only glyphs name fixed keys: the arrow keys steer every menu.
const char *fixed_label(const std::string &glyph) {
    static const std::map<std::string, const char *> table{
        {"analog", "WASD"}, {"analog_Small", "WASD"}, {"d_pad", "ARROWS"},
        // The arrow keys are the d-pad everywhere (menus and HUD prompts such
        // as the hero offer's accept / decline); drawn as arrows.
        {"d_pad_up", "\x01" "U"}, {"d_pad_dn", "\x01" "D"}, {"d_pad_lf", "\x01" "L"}, {"d_pad_rt", "\x01" "R"},
        {"d_pad_lf_Small", "\x01" "L"}, {"d_pad_rt_Small", "\x01" "R"},
    };
    const auto it = table.find(glyph);
    return it == table.end() ? nullptr : it->second;
}

void fill(Texture &t, int x, int y, int w, int h, std::array<std::uint8_t, 4> c) {
    for (int j = std::max(0, y); j < std::min<int>(t.height, y + h); ++j)
        for (int i = std::max(0, x); i < std::min<int>(t.width, x + w); ++i)
            std::memcpy(&t.rgba[(std::size_t(j) * t.width + i) * 4u], c.data(), 4);
}
// A key cap: dark face, light edge, the key's name centred in the menu font.
void key_cap(Texture &t, int x, int y, int w, int h, const std::string &label) {
    fill(t, x, y, w, h, {0, 0, 0, 0});
    const int inset = std::max(1, std::min(w, h) / 14);
    x += inset; y += inset; w -= 2 * inset; h -= 2 * inset;
    if (w < 6 || h < 6) return;
    const int edge = std::max(1, std::min(w, h) / 16);
    fill(t, x + edge, y, w - 2 * edge, h, {214, 222, 234, 255});
    fill(t, x, y + edge, w, h - 2 * edge, {214, 222, 234, 255});
    fill(t, x + edge * 2, y + edge, w - edge * 4, h - edge * 2, {22, 28, 40, 245});
    fill(t, x + edge, y + edge * 2, w - edge * 2, h - edge * 4, {22, 28, 40, 245});
    if (label.size() == 2 && label[0] == '\x01') {
        // Arrow key: a solid triangle pointing the key's way.
        const int cx = x + w / 2, cy = y + h / 2, r = std::min(w, h) * 3 / 10;
        for (int j = -r; j <= r; ++j)
            for (int i = -r; i <= r; ++i) {
                int along = 0, across = 0;  // along: distance from the tip backwards
                switch (label[1]) {
                case 'L': along = i + r; across = j; break;
                case 'R': along = r - i; across = j; break;
                case 'U': along = j + r; across = i; break;
                default: along = r - j; across = i; break;
                }
                if (std::abs(across) * 2 <= along) fill(t, cx + i, cy + j, 1, 1, {245, 248, 252, 255});
            }
        return;
    }
    using game_font::Face;
    int scale = 1;
    for (int s = 6; s >= 1; --s)
        if (game_font::text_width(Face::Small, label, s) <= w - edge * 6 && game_font::height(Face::Small, s) <= h * 7 / 10) { scale = s; break; }
    std::vector<std::byte> canvas(t.rgba.size());
    std::memcpy(canvas.data(), t.rgba.data(), t.rgba.size());
    const int tw = game_font::text_width(Face::Small, label, scale), th = game_font::height(Face::Small, scale);
    game_font::draw(canvas, t.width, t.height, x + (w - tw) / 2, y + (h - th) / 2, label, Face::Small, scale, {245, 248, 252});
    std::memcpy(t.rgba.data(), canvas.data(), t.rgba.size());
}
}  // namespace

bool active() { return input008::keyboard_mouse_active(); }

std::shared_ptr<overrides::Texture> keyboard_variant(const std::string &name, const overrides::Texture &base,
                                          const std::filesystem::path &game_data_root) {
    if (!game_font::loaded() || base.width == 0 || base.height == 0) return {};
    const auto label_for = [](const std::string &glyph) -> std::string {
        if (const char *binding = binding_for(glyph)) return vcs::display_window_key_label(binding);
        if (const char *fixed = fixed_label(glyph)) return fixed;
        return {};
    };
    if (name == "pspbuttons") {
        static const auto regions = load_regions(game_data_root / "PSP_GAME" / "USRDIR" / "GRAPHICS" / "PSPBUTTONS.ASR");
        if (regions.empty()) return {};
        auto out = std::make_shared<Texture>(base);
        out->normal_map.reset();
        for (const auto &[glyph, r] : regions) {
            const std::string label = label_for(glyph);
            if (label.empty()) continue;  // objective arrows, skull, command post...: keep the picture
            const int x0 = static_cast<int>(std::lround(r.u0 * out->width)), y0 = static_cast<int>(std::lround(r.v0 * out->height));
            const int x1 = static_cast<int>(std::lround(r.u1 * out->width)), y1 = static_cast<int>(std::lround(r.v1 * out->height));
            key_cap(*out, x0, y0, x1 - x0, y1 - y0, label);
        }
        return out;
    }
    if (name.rfind("button_", 0) == 0) {
        const std::string label = label_for(name);
        if (label.empty()) return {};
        auto out = std::make_shared<Texture>(base);
        out->normal_map.reset();
        key_cap(*out, 0, 0, static_cast<int>(out->width), static_cast<int>(out->height), label);
        return out;
    }
    return {};
}
}  // namespace renegade::key_prompts
