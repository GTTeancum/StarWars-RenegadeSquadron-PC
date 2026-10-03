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
}
