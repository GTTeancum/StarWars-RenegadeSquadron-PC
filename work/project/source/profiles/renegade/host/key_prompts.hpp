#pragma once
// Keyboard/mouse button prompts.
//
// The game draws every on-screen button prompt from GRAPHICS\PSPBUTTONS.ASR
// (one atlas, regions named in its TTXT table) and a few single-button
// textures (button_*). The texture pack replaces them with Xbox controller
// glyphs; while the keyboard and mouse are the live device, these are redrawn
// as key caps naming the bound keys (the [Keyboard] settings), in the game's
// own menu font. Own design: Asura PC draws prompts from its own PC atlas,
// which Renegade does not ship.
#include "override_texture.hpp"
#include <filesystem>
#include <memory>
#include <string>

namespace renegade::key_prompts {
// True while keyboard/mouse prompts should be shown.
bool active();
// The key-cap version of a prompt texture, or null when the texture is not a
// prompt texture (or the game font is not loaded yet). name is the texture's
// name from names.tsv; base is the pad replacement being shown otherwise.
std::shared_ptr<overrides::Texture> keyboard_variant(const std::string &name, const overrides::Texture &base,
                                          const std::filesystem::path &game_data_root);
}

namespace vcs {
// Short label for the key bound to a pad button (binding names as in
// RENEGADE_KEY_<name>: A B X Y Back Start LS RS LB RB Up Down Left Right LT RT).
std::string display_window_key_label(const char *binding);
}
