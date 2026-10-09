#include "game_font.hpp"
#include <algorithm>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <unordered_map>

namespace renegade::game_font {
namespace {
struct Texture { unsigned width{}, height{}; std::vector<std::uint32_t> rgba; };
struct Glyph { float u, v, width; const Texture *texture; unsigned texture_height; };
struct Font {
    float height{};
    std::unordered_map<std::uint32_t, Glyph> glyphs;
};
std::map<std::string, Texture> textures;  // by lower-case file name
Font fonts[2];
bool ready = false;

std::uint32_t u32(const std::vector<std::uint8_t> &b, std::size_t at) { std::uint32_t v; std::memcpy(&v, b.data() + at, 4); return v; }
std::uint16_t u16(const std::vector<std::uint8_t> &b, std::size_t at) { std::uint16_t v; std::memcpy(&v, b.data() + at, 2); return v; }
float f32(const std::vector<std::uint8_t> &b, std::size_t at) { float v; std::memcpy(&v, b.data() + at, 4); return v; }
std::string lower_leaf(std::string name) {
    const auto slash = name.find_last_of("\\/");
    if (slash != std::string::npos) name.erase(0, slash + 1);
    for (char &c : name) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return name;
}
}  // namespace

bool load(const std::filesystem::path &fonts_asr) {
    std::ifstream file(fonts_asr, std::ios::binary);
    if (!file) return false;
    std::vector<std::uint8_t> b((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    struct PageRef { std::string texture; Font *font; std::vector<Glyph> glyphs; };
    std::vector<PageRef> pages;
    std::size_t p = 8;
    while (p + 16 <= b.size()) {
        const std::string tag(reinterpret_cast<const char *>(b.data() + p), 4);
        const std::uint32_t size = u32(b, p + 4);
        if (size < 16 || p + size > b.size()) break;
        if (tag == "RSCF") {
            // Asura_PSP texture: name, then w/h/flags/format/mips, IDX8 pixels, 256-entry 8888 CLUT.
            std::size_t q = p + 28;
            const std::size_t end = std::find(b.begin() + q, b.end(), 0) - b.begin();
            const std::string name = lower_leaf(std::string(reinterpret_cast<const char *>(b.data() + q), end - q));
            q = (end + 1 + 3) & ~std::size_t(3);
            const unsigned w = u16(b, q), h = u16(b, q + 2), flags = u16(b, q + 4), fmt = b[q + 6];
            q += 8;
            if (fmt == 5 && flags == 0 && q + std::size_t(w) * h + 1024 <= b.size()) {
                Texture t; t.width = w; t.height = h; t.rgba.resize(std::size_t(w) * h);
                const std::size_t clut = q + std::size_t(w) * h;
                // PSP swizzle: 16-byte x 8-row blocks (Asura_PSP_TextureManagement loads the
                // pages swizzled; the IDX8 row is w bytes wide).
                for (unsigned y = 0; y < h; ++y)
                    for (unsigned x = 0; x < w; ++x) {
                        const std::size_t block = (std::size_t(y / 8u) * ((w + 15u) / 16u) + x / 16u) * 128u + (y & 7u) * 16u + (x & 15u);
                        t.rgba[std::size_t(y) * w + x] = u32(b, clut + 4u * b[q + block]);
                    }
                textures[name] = std::move(t);
            }
        } else if (tag == "FONT") {
            std::size_t q = p + 16;
            const std::string name(reinterpret_cast<const char *>(b.data() + q), strnlen(reinterpret_cast<const char *>(b.data() + q), 100));
            q += 100;
            const float height = f32(b, q); const std::uint32_t npages = u32(b, q + 4); q += 8;
            Font *font = name.find("_13") != std::string::npos ? &fonts[0] : name.find("_9") != std::string::npos ? &fonts[1] : nullptr;
            for (std::uint32_t i = 0; i < npages && q + 124 <= b.size(); ++i) {
                PageRef page; page.font = font;
                page.texture = lower_leaf(std::string(reinterpret_cast<const char *>(b.data() + q), strnlen(reinterpret_cast<const char *>(b.data() + q), 100)));
                q += 100;
                const std::uint32_t nchars = u32(b, q + 20); q += 24;
                for (std::uint32_t g = 0; g < nchars && q + 16 <= b.size(); ++g, q += 16)
                    page.glyphs.push_back(Glyph{f32(b, q), f32(b, q + 4), f32(b, q + 8), nullptr, 0u}),
                    page.glyphs.back().texture_height = u16(b, q + 12);  // the character code, resolved below
                if (font) font->height = height;
                pages.push_back(std::move(page));
            }
        }
        p += size;
    }
    for (PageRef &page : pages) {
        if (!page.font) continue;
        const auto tex = textures.find(page.texture);
        if (tex == textures.end()) continue;
        for (Glyph g : page.glyphs) {
            const std::uint32_t code = g.texture_height;
            g.texture = &tex->second; g.texture_height = tex->second.height;
            page.font->glyphs[code] = g;
        }
    }
    ready = !fonts[0].glyphs.empty() && !fonts[1].glyphs.empty();
    if (!ready) std::cerr << "[game-font] " << fonts_asr.string() << ": fonts not found\n";
    return ready;
}

bool loaded() { return ready; }

int height(Face face, int scale) { return static_cast<int>(fonts[face == Face::Large ? 0 : 1].height) * scale; }

int text_width(Face face, const std::string &text, int scale) {
    const Font &font = fonts[face == Face::Large ? 0 : 1];
    int x = 0;
    for (unsigned char c : text) {
        const auto it = font.glyphs.find(c);
        x += (it == font.glyphs.end() ? static_cast<int>(font.height / 3) : static_cast<int>(it->second.width)) * scale;
    }
    return x;
}

void draw(std::vector<std::byte> &rgba, unsigned width, unsigned height_px, int x, int y, const std::string &text,
          Face face, int scale, Rgb tint) {
    if (!ready || scale < 1) return;
    const Font &font = fonts[face == Face::Large ? 0 : 1];
    const int glyph_height = static_cast<int>(font.height);
    for (unsigned char c : text) {
        const auto it = font.glyphs.find(c);
        if (it == font.glyphs.end()) { x += static_cast<int>(font.height / 3) * scale; continue; }
        const Glyph &g = it->second;
        const Texture &t = *g.texture;
        const int sx0 = static_cast<int>(g.u * t.width + 0.5f), sy0 = static_cast<int>(g.v * t.height + 0.5f);
        const int gw = static_cast<int>(g.width);
        for (int gy = 0; gy < glyph_height; ++gy)
            for (int gx = 0; gx < gw; ++gx) {
                const int sx = sx0 + gx, sy = sy0 + gy;
                if (sx < 0 || sy < 0 || sx >= static_cast<int>(t.width) || sy >= static_cast<int>(t.height)) continue;
                const std::uint32_t texel = t.rgba[std::size_t(sy) * t.width + sx];
                const unsigned alpha = (texel >> 24) & 0xFFu, luma = texel & 0xFFu;
                if (alpha == 0) continue;
                // Glyph pages are white lettering; tint by the requested colour.
                const unsigned a = alpha * luma / 255u;
                for (int dy = 0; dy < scale; ++dy)
                    for (int dx = 0; dx < scale; ++dx) {
                        const int px = x + gx * scale + dx, py = y + gy * scale + dy;
                        if (px < 0 || py < 0 || px >= static_cast<int>(width) || py >= static_cast<int>(height_px)) continue;
                        std::byte *d = rgba.data() + (std::size_t(py) * width + px) * 4;
                        const unsigned inv = 255u - a;
                        d[0] = std::byte((tint.r * a + std::to_integer<unsigned>(d[0]) * inv) / 255u);
                        d[1] = std::byte((tint.g * a + std::to_integer<unsigned>(d[1]) * inv) / 255u);
                        d[2] = std::byte((tint.b * a + std::to_integer<unsigned>(d[2]) * inv) / 255u);
                        d[3] = std::byte(std::min(255u, a + std::to_integer<unsigned>(d[3]) * inv / 255u));
                    }
            }
        x += gw * scale;
    }
}
}  // namespace renegade::game_font
