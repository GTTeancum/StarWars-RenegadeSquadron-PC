#pragma once
#include <cstdint>
#include <cstddef>
#include <string>
#include <vector>
namespace vcs {
// Host presentation of a PSP system message. This is not a guest-state override.
struct MessageDialogView {
    bool visible{}, yes_no{}, ok{}, cancel{}, accept_cross{true}, selected_yes{true};
    unsigned scroll{};
    std::string text;
};
void display_window_set_message_dialog(const MessageDialogView& view);
MessageDialogView display_window_message_dialog();
// Direct GPU presentation only: the visible message as a transparent RGBA image.
bool display_window_dialog_overlay(std::vector<std::byte>& rgba, unsigned& width, unsigned& height);
// PC text entry replacing the PSP on-screen keyboard (sceUtilityOsk*).
void display_window_begin_text_entry(const std::string& title, const std::string& initial, std::size_t limit);
// True once the player confirmed (Enter / A) or cancelled (Esc / B).
bool display_window_text_entry_result(std::string& text, bool& cancelled);
void display_window_end_text_entry();
}
