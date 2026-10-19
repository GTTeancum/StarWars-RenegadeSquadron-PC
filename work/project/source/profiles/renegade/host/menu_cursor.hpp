#pragma once
// Mouse cursor for the game's menus.
//
// Asura PC drives its GUIMenu pages from the OS cursor: Asura_GUIMenu_System
// fills Asura_GUIMenu_Input::m_xCursorPos from Asura_Cursor::GetScreenSpaceCoords
// and Asura_GUIMenu_Menu_Page::ProcessInputActivity selects the selectable widget
// under the cursor (FindSelectableWidgetAtPos), sending ON_ROLL_IN / ON_ROLL_OUT
// and playing the cursor-navigate sound; a click is ASURA_GUIMENU_ACTION_BUTTON_CLICK,
// which the widgets treat as accept.
//
// Renegade's PSP build was compiled without ASURA_USE_CURSOR, so the host does
// that page step itself each vblank, on the game's live menu objects: the
// focused page (Asura_GUIMenu_System::s_apxMenuPages[s_iSelectedMenuIndex]),
// its widgets' screen rectangles, and the same message pump the engine uses.
#include "psprecomp/runtime.hpp"
#include <cstdint>

namespace vcs {
struct MenuCursorState {
    bool available{};   // a cursor position exists (window pointer or injected)
    float x{}, y{};     // PSP screen coordinates (480x272)
    bool left{}, right{}, middle{};
    int wheel{};        // wheel notches since the last call (positive = up)
};
// Current cursor as seen by the host window (or the diagnostics channel).
MenuCursorState display_window_menu_cursor();
// The menu module reports whether a page is taking cursor input and whether the
// cursor is over a selectable widget: the window then draws the cursor, releases
// the mouse capture, and turns the left button into accept only over a widget.
// click_buttons: the PSP buttons a left click sends over this widget (accept,
// a numeric's left/right step, or none where the click is handled here).
void display_window_set_menu_cursor(bool page_active, bool over_widget, std::uint32_t click_buttons = 0x4000u);
// PSP buttons the menu module holds this vblank (a scripted press sequence).
void display_window_set_menu_buttons(std::uint32_t buttons);
}

namespace renegade::menu_cursor {
// Once per vblank from the main thread, after pc_settings::poll.
void poll(psprecomp::Runtime &rt, psprecomp::AllegrexContext &ctx);
}
