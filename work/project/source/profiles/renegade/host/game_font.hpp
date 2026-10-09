#pragma once
// The game's own menu fonts (GRAPHICS\FONTS.ASR, Asura_Chunk_Font version 3 with
// IDX8 glyph pages) for host-drawn overlays, so the PC text entry and system
// message boxes use the same lettering as the menus.
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

namespace renegade::game_font {
enum class Face { Large, Small };  // Franklin Gothic Medium Cond 13 / 9
struct Rgb { std::uint8_t r, g, b; };

bool load(const std::filesystem::path &fonts_asr);
bool loaded();
// Pixel height of a face at the given integer scale.
int height(Face face, int scale);
int text_width(Face face, const std::string &text, int scale);
// Alpha-blends the text into an RGBA canvas (top-left at x, y).
void draw(std::vector<std::byte> &rgba, unsigned width, unsigned height, int x, int y, const std::string &text,
          Face face, int scale, Rgb tint);
}
