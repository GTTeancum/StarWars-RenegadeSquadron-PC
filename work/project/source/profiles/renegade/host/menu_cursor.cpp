// Mouse cursor for the game's menus: the host performs the cursor part of
// Asura_GUIMenu_Menu_Page::ProcessInputActivity on the live menu objects.
// See menu_cursor.hpp for the engine background.
#include "menu_cursor.hpp"
#include "pc_settings.hpp"
#include "control_context009.hpp"
#include "modern_input008.hpp"
#include "psprecomp/common.hpp"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <deque>
#include <string>

namespace renegade::menu_cursor {
namespace {
// Asura_GUIMenu_System statics (ULUS10292).
constexpr std::uint32_t kSelectedMenuIndex = 0x08B15FA0u;  // s_iSelectedMenuIndex
constexpr std::uint32_t kMenuPages = 0x08B29978u;          // s_apxMenuPages[128]
constexpr std::uint32_t kMenuPageUsage = 0x08B29B78u;      // s_aucMenuPageUsageFlags[128], bit 0 = active
constexpr std::uint32_t kMenuPageCount = 0x08B29BF8u;      // s_uMenuPageCount
// Asura_GUIMenu_MessagePump::PostMessage(to, from, action, widget type, data)
constexpr std::uint32_t kPostMessage = 0x08885E0Cu;
constexpr std::uint32_t kMsgOnRollIn = 4u;   // ASURA_GUIMENU_UI_MSG_ON_ROLL_IN
constexpr std::uint32_t kMsgOnRollOut = 5u;  // ASURA_GUIMENU_UI_MSG_ON_ROLL_OUT

// Asura_GUIMenu_Root (2007 layout, read from the running game against the
// page data): type, local and screen positions, container parts, hash ID.
constexpr std::uint32_t oType = 0x04u;
constexpr std::uint32_t oScreenX = 0x14u, oScreenY = 0x18u;
constexpr std::uint32_t oParts = 0x30u, oPartCount = 0x34u;
constexpr std::uint32_t oHashID = 0x90u;
// Asura_GUIMenu_Element_Base::m_xDimensions
constexpr std::uint32_t oElementWidth = 0x98u, oElementHeight = 0x9Cu;
// Asura_GUIMenu_Widget_Base::m_bSelectable / m_bCanBeSelectable (IsSelectable = both)
constexpr std::uint32_t oSelectable = 0x98u, oCanBeSelectable = 0x99u;
// Asura_GUIMenu_Menu_Page: m_pxActiveWidget, m_uHashActiveWidget, m_uState
constexpr std::uint32_t oActiveWidget = 0x98u, oActiveWidgetHash = 0x9Cu, oPageState = 0xECu;
constexpr std::uint32_t kPageStateActive = 0x2000u;  // ASURA_GUIMENU_ACTION_FLAG_IS_MENU_ACTIVE
// Asura_CommandConsole_VarRepository::Find(const wchar_t *name) -> Var*, and the
// Var node: type (0 bool, 1 int, 2 float), bound value pointer, limits.
constexpr std::uint32_t kFindVar = 0x088992A4u;
constexpr std::uint32_t oVarType = 0x10u, oVarValue = 0x18u, oVarLow = 0x1Cu, oVarHigh = 0x20u;
// Asura_GUIMenu_Widget_Slider (read from the running game on the Gamepad &
// Mouse page): m_pxPath, m_fPosition, the value step, the console variable's
// limits (m_fConsoleVarLowerLimit/UpperLimit) and name (Asura_String: pointer
// to the characters, length, capacity).
constexpr std::uint32_t kTypeSlider = 2003u, kTypePath = 1003u;
constexpr std::uint32_t oSliderPosition = 0xB4u, oSliderStep = 0xC8u, oSliderLow = 0xD8u, oSliderHigh = 0xDCu, oSliderVarName = 0xE0u;
constexpr std::uint32_t kTypeElementFirst = 1001u, kTypeElementLast = 1006u, kTypeWidgetFirst = 2001u;
constexpr std::uint32_t kTypeGroup = 2006u;  // Asura_GUIMenu_Widget_Group only searches its children
// Asura_GUIMenu_Widget_TextListBox (read from the running game on the Instant
// Action page): m_pxBoundingRects (one screen rectangle per entry, x0 y0 x1 y1,
// placed for the rows being drawn), m_uEntryCount, list width/height, m_uSelectedIndex,
// m_fDisplayListOffsetY (the rows drawn; the game resets the target value
// beside it), m_fDisplayTargetOffsetY, m_fMoveDir and m_uMaxDisplayedEntries.
constexpr std::uint32_t kTypeTextListBox = 2005u, kTypeNumeric = 2009u;
constexpr std::uint32_t oListRects = 0xC8u, oListCount = 0xF0u, oListWidth = 0xF4u, oListHeight = 0xF8u,
                        oListSelected = 0xFCu, oListOffset = 0x104u, oListTargetOffset = 0x108u, oListMoveDir = 0x10Cu,
                        oListMaxDisplayed = 0x114u;
// Asura_GUIMenu_Element_Text: the text ID it shows (hash of the string's name).
constexpr std::uint32_t oTextId = 0xB8u;
// Asura_GUIMenu_Root::m_uFlags: RENDERING_DISABLED (1<<8), IS_HIDDEN_BY_COND_VAR (1<<9).
constexpr std::uint32_t oHiddenFlags = 0x74u, kHidden = 0x300u;
constexpr std::uint32_t kTypeText = 1002u;
// PSP buttons the window adds for a left click (Asura's CLICK as the widgets read it).
constexpr std::uint32_t kButtonAccept = 0x4000u, kButtonLeft = 0x80u, kButtonRight = 0x20u;

bool valid_object(std::uint32_t address) {
    return address >= 0x08800000u && address < 0x0A000000u && (address & 3u) == 0u;
}
float load_float(const psprecomp::GuestMemory &m, std::uint32_t address) {
    const std::uint32_t bits = m.load32(address);
    float value;
    std::memcpy(&value, &bits, sizeof value);
    return std::isfinite(value) ? value : 0.0f;
}
// Asura_GUIMenu_Root::ContainsPos for an element: its screen rectangle.
bool element_contains(const psprecomp::GuestMemory &m, std::uint32_t element, float x, float y) {
    const float left = load_float(m, element + oScreenX), top = load_float(m, element + oScreenY);
    const float width = load_float(m, element + oElementWidth), height = load_float(m, element + oElementHeight);
    if (width <= 0.0f || height <= 0.0f) return false;
    return x >= left && y >= top && x < left + width && y < top + height;
}
// Asura_GUIMenu_Widget_Base::FindSelectableWidgetAtPos: a selectable widget
// with a container part under the cursor, otherwise the search continues
// into the children (Asura_GUIMenu_Root::FindSelectableWidgetAtPos).
std::uint32_t find_selectable_widget_at(const psprecomp::GuestMemory &m, std::uint32_t object, float x, float y,
                                        int depth, bool images_only) {
    if (!valid_object(object) || depth > 8) return 0u;
    const std::uint32_t type = m.load32(object + oType);
    const std::uint32_t parts = m.load32(object + oParts);
    const std::uint32_t count = std::min<std::uint32_t>(m.load32(object + oPartCount), 512u);
    if (!valid_object(parts) && count) return 0u;
    if (type >= kTypeWidgetFirst && type != kTypeGroup && m.load8(object + oSelectable) && m.load8(object + oCanBeSelectable)) {
        if (type == kTypeTextListBox) {
            const float left = load_float(m, object + oScreenX), top = load_float(m, object + oScreenY);
            if (x >= left && y >= top && x < left + load_float(m, object + oListWidth) && y < top + load_float(m, object + oListHeight))
                return object;
        }
        for (std::uint32_t i = 0; i < count; ++i) {
            const std::uint32_t part = m.load32(parts + 4u * i);
            if (!valid_object(part)) continue;
            const std::uint32_t part_type = m.load32(part + oType);
            if (images_only && part_type != kTypeElementFirst) continue;
            if (part_type >= kTypeElementFirst && part_type <= kTypeElementLast && element_contains(m, part, x, y))
                return object;
        }
    }
    for (std::uint32_t i = 0; i < count; ++i) {
        const std::uint32_t part = m.load32(parts + 4u * i);
        if (!valid_object(part)) continue;
        const std::uint32_t part_type = m.load32(part + oType);
        if (part_type < kTypeWidgetFirst) continue;  // elements have no selectable children
        if (const std::uint32_t found = find_selectable_widget_at(m, part, x, y, depth + 1, images_only)) return found;
    }
    return 0u;
}

// Asura_GUIMenu_Widget_Slider cursor drag: a click on the slider starts a drag
// and the value follows the cursor along the bar (SetSliderFromCursorPos ->
// SetConsoleVar). The PSP style draws the value as a row of small segment
// images, so the bar is the extent of those segments; the path element (the
// engine's own drag area) is the fallback, then the widget's whole width.
bool slider_bar(const psprecomp::GuestMemory &m, std::uint32_t slider, float &left, float &right) {
    const std::uint32_t parts = m.load32(slider + oParts);
    const std::uint32_t count = std::min<std::uint32_t>(m.load32(slider + oPartCount), 512u);
    if (!valid_object(parts)) return false;
    float seg_left = 1e9f, seg_right = -1e9f, path_left = 0.f, path_right = 0.f, all_left = 1e9f, all_right = -1e9f;
    bool path = false;
    for (std::uint32_t i = 0; i < count; ++i) {
        const std::uint32_t part = m.load32(parts + 4u * i);
        if (!valid_object(part)) continue;
        const std::uint32_t type = m.load32(part + oType);
        if (type < kTypeElementFirst || type > kTypeElementLast) continue;
        const float x = load_float(m, part + oScreenX), w = load_float(m, part + oElementWidth), h = load_float(m, part + oElementHeight);
        if (w <= 0.f || h <= 0.f) continue;
        all_left = std::min(all_left, x); all_right = std::max(all_right, x + w);
        if (type == kTypePath) { path = true; path_left = x; path_right = x + w; }
        else if (type == kTypeElementFirst && w <= 20.f && h <= 12.f) { seg_left = std::min(seg_left, x); seg_right = std::max(seg_right, x + w); }
    }
    if (seg_right > seg_left) { left = seg_left; right = seg_right; return true; }
    if (path && path_right > path_left) { left = path_left; right = path_right; return true; }
    if (all_right > all_left) { left = all_left; right = all_right; return true; }
    return false;
}
std::string load_cstring(const psprecomp::GuestMemory &m, std::uint32_t address) {
    std::string out;
    if (!valid_object(address & ~3u)) return out;
    for (std::uint32_t i = 0; i < 64u; ++i) {
        const char c = static_cast<char>(m.load8(address + i));
        if (c == '\0') break;
        out.push_back(c);
    }
    return out;
}
void drag_slider(psprecomp::Runtime &rt, psprecomp::AllegrexContext &ctx, std::uint32_t slider, float cursor_x, bool diagnostics) {
    auto &m = rt.memory();
    float left = 0.f, right = 0.f;
    if (!slider_bar(m, slider, left, right)) return;
    const float fraction = std::clamp((cursor_x - left) / (right - left), 0.0f, 1.0f);
    const std::string name = load_cstring(m, m.load32(slider + oSliderVarName));
    if (name.empty()) return;
    const std::uint32_t var = pc_settings::call_guest_routine(rt, ctx, kFindVar, {pc_settings::scratch_wide_string(rt, name.c_str())});
    if (!valid_object(var)) return;
    const std::uint32_t type = m.load32(var + oVarType), value_at = m.load32(var + oVarValue);
    if (!valid_object(value_at & ~3u) || type > 2u) return;
    const float step = load_float(m, slider + oSliderStep);
    if (type == 2u) {
        // Asura_GUIMenu_Widget_Slider::SetConsoleVar: value = position * range + lower limit.
        float low = load_float(m, slider + oSliderLow), high = load_float(m, slider + oSliderHigh);
        if (high == low) { low = load_float(m, var + oVarLow); high = load_float(m, var + oVarHigh); }
        if (high == low) return;
        float value = low + (high - low) * fraction;
        if (step > 0.f) value = low + std::round((value - low) / step) * step;
        value = std::clamp(value, std::min(low, high), std::max(low, high));
        const float position = (value - low) / (high - low);
        std::uint32_t bits, position_bits;
        std::memcpy(&bits, &value, sizeof bits);
        std::memcpy(&position_bits, &position, sizeof position_bits);
        m.store32(slider + oSliderPosition, position_bits);
        if (m.load32(value_at) != bits) { m.store32(value_at, bits); if (diagnostics) std::cerr << "[menu-cursor] " << name << " = " << value << "\n"; }
    } else if (type == 1u) {
        const std::int32_t low = static_cast<std::int32_t>(m.load32(var + oVarLow)), high = static_cast<std::int32_t>(m.load32(var + oVarHigh));
        const std::int32_t value = std::clamp(static_cast<std::int32_t>(std::lround(low + (high - low) * fraction)), std::min(low, high), std::max(low, high));
        if (static_cast<std::int32_t>(m.load32(value_at)) != value) { m.store32(value_at, static_cast<std::uint32_t>(value)); if (diagnostics) std::cerr << "[menu-cursor] " << name << " = " << value << "\n"; }
    }
}

// Selectable widgets anywhere on the page (Asura_GUIMenu_Widget_Base::IsSelectable).
// A page without any (the PRESS START screen, status pages) takes no cursor
// input: a click there is plain accept, like the pad's button.
std::uint32_t count_selectable(const psprecomp::GuestMemory &m, std::uint32_t object, int depth) {
    if (!valid_object(object) || depth > 8) return 0u;
    const std::uint32_t type = m.load32(object + oType);
    std::uint32_t n = (type >= kTypeWidgetFirst && type != kTypeGroup && m.load8(object + oSelectable) &&
                       m.load8(object + oCanBeSelectable)) ? 1u : 0u;
    const std::uint32_t parts = m.load32(object + oParts);
    const std::uint32_t count = std::min<std::uint32_t>(m.load32(object + oPartCount), 512u);
    if (!valid_object(parts)) return n;
    for (std::uint32_t i = 0; i < count; ++i) {
        const std::uint32_t part = m.load32(parts + 4u * i);
        if (valid_object(part) && m.load32(part + oType) >= kTypeWidgetFirst) n += count_selectable(m, part, depth + 1);
    }
    return n;
}

// Asura_GUIMenu_Widget_TextListBox::ProcessInputActivity with the cursor: the
// visible row under the cursor becomes the selected entry (m_uSelectedIndex),
// and a click accepts it. Returns the entry, or -1 when no row is under it.
int list_row_at(const psprecomp::GuestMemory &m, std::uint32_t list, float x, float y) {
    const std::uint32_t rects = m.load32(list + oListRects);
    if (!valid_object(rects)) return -1;
    const std::uint32_t count = m.load32(list + oListCount);
    const std::uint32_t shown = std::min<std::uint32_t>(m.load32(list + oListMaxDisplayed), 64u);
    // One rectangle per entry, placed on screen for the rows being drawn.
    const int offset = std::max(0, static_cast<int>(std::lround(load_float(m, list + oListOffset))));
    for (int entry = offset; entry < offset + static_cast<int>(shown) && entry < static_cast<int>(count); ++entry) {
        const std::uint32_t r = rects + 16u * static_cast<std::uint32_t>(entry);
        const float x0 = load_float(m, r), y0 = load_float(m, r + 4u), x1 = load_float(m, r + 8u), y1 = load_float(m, r + 12u);
        if (x >= x0 && x < x1 && y >= y0 && y < y1) return entry;
    }
    return -1;
}
// Button prompts: the menus write "<icon> Personalization Menu", "Back <icon>"
// and so on with icon strings (menu text BU_CROSS, BU_SQUARE...). Clicking a
// prompt presses the button it shows, so every prompt is a mouse button too.
std::uint32_t asura_hash(const char *text) {
    std::uint32_t h = 0;
    for (const char *c = text; *c; ++c) {
        char ch = *c;
        if (ch >= 'A' && ch <= 'Z') ch = static_cast<char>(ch - 'A' + 'a');
        if (ch == 92) ch = '/';
        h = h * 31u + static_cast<unsigned char>(ch);
    }
    return h;
}
std::uint32_t icon_button(std::uint32_t text_id) {
    static const std::pair<std::uint32_t, std::uint32_t> table[] = {
        {asura_hash("BU_CROSS"), 0x4000u}, {asura_hash("BU_CIRCLE"), 0x2000u}, {asura_hash("BU_SQUARE"), 0x8000u},
        {asura_hash("BU_TRIANGLE"), 0x1000u}, {asura_hash("BU_BIG_CROSS"), 0x4000u}, {asura_hash("BU_BIG_CIRCLE"), 0x2000u},
        {asura_hash("BU_BIG_SQUARE"), 0x8000u}, {asura_hash("BU_BIG_TRIANGLE"), 0x1000u},
        {asura_hash("BU_DPAD_UP"), 0x10u}, {asura_hash("BU_DPAD_DOWN"), 0x40u}, {asura_hash("BU_DPAD_LEFT"), 0x80u},
        {asura_hash("BU_DPAD_RIGHT"), 0x20u}, {asura_hash("BU_[_L_]"), 0x100u}, {asura_hash("BU_[_R_]"), 0x200u},
        {asura_hash("BU_[START]"), 0x8u}, {asura_hash("BU_[SELECT]"), 0x1u}};
    for (const auto &[id, button] : table) if (id == text_id) return button;
    return 0u;
}
struct Rect { float x0 = 1e9f, y0 = 1e9f, x1 = -1e9f, y1 = -1e9f; };
void grow(Rect &r, const psprecomp::GuestMemory &m, std::uint32_t element) {
    const float x = load_float(m, element + oScreenX), y = load_float(m, element + oScreenY);
    const float w = load_float(m, element + oElementWidth), h = load_float(m, element + oElementHeight);
    if (w <= 0.f || h <= 0.f) return;
    r.x0 = std::min(r.x0, x); r.y0 = std::min(r.y0, y); r.x1 = std::max(r.x1, x + w); r.y1 = std::max(r.y1, y + h);
}
bool inside(const Rect &r, float x, float y) { return x >= r.x0 && x < r.x1 && y >= r.y0 && y < r.y1; }
// The button of the prompt under the cursor, or 0.
std::uint32_t prompt_at(const psprecomp::GuestMemory &m, std::uint32_t page, float x, float y) {
    const std::uint32_t parts = m.load32(page + oParts);
    const std::uint32_t count = std::min<std::uint32_t>(m.load32(page + oPartCount), 512u);
    if (!valid_object(parts)) return 0u;
    for (std::uint32_t i = 0; i < count; ++i) {
        const std::uint32_t part = m.load32(parts + 4u * i);
        if (!valid_object(part) || m.load32(part + oHiddenFlags) & kHidden) continue;
        const std::uint32_t type = m.load32(part + oType);
        if (type >= kTypeWidgetFirst) {
            // a widget whose elements include a button icon: its whole line is the prompt
            const std::uint32_t cp = m.load32(part + oParts), cn = std::min<std::uint32_t>(m.load32(part + oPartCount), 32u);
            if (!valid_object(cp)) continue;
            std::uint32_t button = 0u;
            Rect r;
            for (std::uint32_t k = 0; k < cn; ++k) {
                const std::uint32_t e = m.load32(cp + 4u * k);
                if (!valid_object(e) || m.load32(e + oHiddenFlags) & kHidden) continue;
                const std::uint32_t et = m.load32(e + oType);
                if (et == kTypeText && !button) button = icon_button(m.load32(e + oTextId));
                if (et >= kTypeElementFirst && et <= kTypeElementLast) grow(r, m, e);
            }
            if (button && inside(r, x, y)) return button;
        } else if (type == kTypeText) {
            // a page-level icon ("Select <icon>"): the icon plus the label beside it
            const std::uint32_t button = icon_button(m.load32(part + oTextId));
            if (!button) continue;
            Rect r;
            grow(r, m, part);
            for (std::uint32_t j = 0; j < count; ++j) {
                const std::uint32_t other = m.load32(parts + 4u * j);
                if (!valid_object(other) || other == part || m.load32(other + oHiddenFlags) & kHidden) continue;
                Rect o;
                if (m.load32(other + oType) >= kTypeWidgetFirst) {
                    if (m.load8(other + oSelectable) && m.load8(other + oCanBeSelectable)) continue;
                    const std::uint32_t cp = m.load32(other + oParts), cn = std::min<std::uint32_t>(m.load32(other + oPartCount), 32u);
                    if (!valid_object(cp)) continue;
                    for (std::uint32_t k = 0; k < cn; ++k) { const std::uint32_t e = m.load32(cp + 4u * k); if (valid_object(e)) grow(o, m, e); }
                } else grow(o, m, other);
                if (o.x1 <= o.x0) continue;
                const bool same_line = o.y0 < r.y1 && o.y1 > r.y0 && (o.y1 - o.y0) < 3.f * (r.y1 - r.y0 + 1.f);
                const bool beside = (o.x1 <= r.x0 && r.x0 - o.x1 < 24.f) || (o.x0 >= r.x1 && o.x0 - r.x1 < 24.f);
                if (same_line && beside) { r.x0 = std::min(r.x0, o.x0); r.x1 = std::max(r.x1, o.x1); r.y0 = std::min(r.y0, o.y0); r.y1 = std::max(r.y1, o.y1); }
            }
            if (inside(r, x, y)) return button;
        }
    }
    return 0u;
}
void queue_press(std::deque<std::uint32_t> &q, std::uint32_t buttons) {
    for (int i = 0; i < 4; ++i) q.push_back(buttons);
    for (int i = 0; i < 4; ++i) q.push_back(0u);
}
// Selects a list entry and scrolls the rows so it is shown, as the list's own
// up/down handling does (the PSP lists draw their scroll thumb from the
// selected entry). Offsets are written to both the displayed and target values.
void list_show(psprecomp::GuestMemory &m, std::uint32_t list, int entry, int offset) {
    const int count = static_cast<int>(m.load32(list + oListCount));
    const int shown = static_cast<int>(m.load32(list + oListMaxDisplayed));
    if (count <= 0 || shown <= 0) return;
    entry = std::clamp(entry, 0, count - 1);
    offset = std::clamp(offset, 0, std::max(0, count - shown));
    if (entry < offset) offset = entry;
    if (entry >= offset + shown) offset = entry - shown + 1;
    const float f = static_cast<float>(offset);
    std::uint32_t bits; std::memcpy(&bits, &f, sizeof bits);
    m.store32(list + oListOffset, bits);
    m.store32(list + oListTargetOffset, bits);
    m.store32(list + oListMoveDir, 0u);
    m.store32(list + oListSelected, static_cast<std::uint32_t>(entry));
}
// The scroll bar beside a list: a page group of images (track and thumb) just
// right of the list's rows. Returns the list it scrolls and its track, or 0.
std::uint32_t scroll_bar_at(const psprecomp::GuestMemory &m, std::uint32_t page, float x, float y, float &top, float &height) {
    const std::uint32_t parts = m.load32(page + oParts);
    const std::uint32_t count = std::min<std::uint32_t>(m.load32(page + oPartCount), 512u);
    if (!valid_object(parts)) return 0u;
    for (std::uint32_t i = 0; i < count; ++i) {
        const std::uint32_t group = m.load32(parts + 4u * i);
        if (!valid_object(group) || m.load32(group + oType) != kTypeGroup || (m.load32(group + oHiddenFlags) & kHidden)) continue;
        const std::uint32_t gp = m.load32(group + oParts), gn = std::min<std::uint32_t>(m.load32(group + oPartCount), 8u);
        if (!valid_object(gp) || gn == 0u) continue;
        float x0 = 1e9f, y0 = 1e9f, x1 = -1e9f, y1 = -1e9f;
        bool images = true;
        for (std::uint32_t k = 0; k < gn; ++k) {
            const std::uint32_t e = m.load32(gp + 4u * k);
            if (!valid_object(e) || m.load32(e + oType) != kTypeElementFirst || (m.load32(e + oHiddenFlags) & kHidden)) { images = false; break; }
            const float ex = load_float(m, e + oScreenX), ey = load_float(m, e + oScreenY);
            x0 = std::min(x0, ex); y0 = std::min(y0, ey);
            x1 = std::max(x1, ex + load_float(m, e + oElementWidth)); y1 = std::max(y1, ey + load_float(m, e + oElementHeight));
        }
        // narrow and tall: a scroll bar, not a frame
        if (!images || x1 - x0 > 16.f || y1 - y0 < 40.f) continue;
        if (x < x0 - 4.f || x > x1 + 4.f || y < y0 || y > y1) continue;
        for (std::uint32_t j = 0; j < count; ++j) {
            const std::uint32_t list = m.load32(parts + 4u * j);
            if (!valid_object(list) || m.load32(list + oType) != kTypeTextListBox) continue;
            if (!m.load8(list + oSelectable) || !m.load8(list + oCanBeSelectable)) continue;
            const float lx = load_float(m, list + oScreenX), ly = load_float(m, list + oScreenY);
            const float right = lx + load_float(m, list + oListWidth), bottom = ly + load_float(m, list + oListHeight);
            if (x0 >= right - 4.f && x0 <= right + 16.f && y0 < bottom && y1 > ly) { top = y0; height = y1 - y0; return list; }
        }
    }
    return 0u;
}
// Asura_GUIMenu_Widget_Numeric with the cursor: a click on the decrement or
// increment side steps the value. The PSP numerics draw no arrow images, so
// the left half of the widget decrements and the right half increments.
std::uint32_t numeric_click(const psprecomp::GuestMemory &m, std::uint32_t numeric, float x) {
    const std::uint32_t parts = m.load32(numeric + oParts);
    const std::uint32_t count = std::min<std::uint32_t>(m.load32(numeric + oPartCount), 64u);
    // The arrow box is drawn by the numeric's images; its label text extends to
    // the right and must not move the split, so only images count (all parts
    // when it has none).
    float left = 1e9f, right = -1e9f, image_left = 1e9f, image_right = -1e9f;
    if (valid_object(parts))
        for (std::uint32_t i = 0; i < count; ++i) {
            const std::uint32_t part = m.load32(parts + 4u * i);
            if (!valid_object(part)) continue;
            const float px = load_float(m, part + oScreenX), w = load_float(m, part + oElementWidth);
            if (w <= 0.f) continue;
            left = std::min(left, px); right = std::max(right, px + w);
            if (m.load32(part + oType) == kTypeElementFirst) { image_left = std::min(image_left, px); image_right = std::max(image_right, px + w); }
        }
    if (image_right > image_left) { left = image_left; right = image_right; }
    static const bool diagnostics = std::getenv("RENEGADE_MENU_CURSOR_DIAG") != nullptr;
    if (diagnostics) {
        static float last = -1.f;
        if (x != last) {
            last = x;
            std::cerr << "[menu-cursor] numeric parts " << count << " span " << left << ".." << right << " cursor " << x;
            if (valid_object(parts))
                for (std::uint32_t i = 0; i < count; ++i) {
                    const std::uint32_t part = m.load32(parts + 4u * i);
                    if (valid_object(part)) std::cerr << " [" << m.load32(part + oType) << " " << load_float(m, part + oScreenX) << "+" << load_float(m, part + oElementWidth) << "]";
                }
            std::cerr << std::endl;
        }
    }
    if (right <= left) return kButtonAccept;
    return x < (left + right) * 0.5f ? kButtonLeft : kButtonRight;
}

struct State {
    // Scripted presses, one PSP button mask per vblank: a numeric step plays
    // the pad's own sequence (Accept to edit, the arrow, Accept), a wheel notch
    // outside a list is an up/down press. Each press is held a few vblanks and
    // released, so the game's input sees every one.
    std::deque<std::uint32_t> presses;
    std::uint32_t scroll_list = 0u;  // list whose scroll bar is being dragged
    float track_top = 0.f, track_height = 0.f;
    std::uint32_t page_hash = 0u;  // last focused page (diagnostics)
    float last_x = -1.0f, last_y = -1.0f;
    std::uint32_t dragging = 0u;  // slider widget under a held left button
    int moved_recently = 0;  // vblanks since the cursor moved (Asura: cursor counts for 0.25 s after moving)
    bool left_was_down = false;
    bool diagnostics = std::getenv("RENEGADE_MENU_CURSOR_DIAG") != nullptr;
} s;
}  // namespace

void poll(psprecomp::Runtime &rt, psprecomp::AllegrexContext &ctx) {
    auto &m = rt.memory();
    const auto inactive = [&] { vcs::display_window_set_menu_cursor(false, false); vcs::display_window_set_menu_buttons(0u); s.presses.clear(); s.scroll_list = 0u; };
    if (!pc_settings::guest_ready() || context009::gameplay_input_active()) { inactive(); return; }
    const std::int32_t index = static_cast<std::int32_t>(m.load32(kSelectedMenuIndex));
    if (index < 0 || index >= 128 || index >= static_cast<std::int32_t>(m.load32(kMenuPageCount)) ||
        (m.load8(kMenuPageUsage + static_cast<std::uint32_t>(index)) & 1u) == 0u) { inactive(); return; }
    const std::uint32_t page = m.load32(kMenuPages + 4u * static_cast<std::uint32_t>(index));
    if (!valid_object(page)) { inactive(); return; }
    // Keyboard/mouse must be the live device (a gamepad player sees no cursor).
    if (!input008::keyboard_mouse_active()) { inactive(); return; }
    const std::uint32_t selectable = count_selectable(m, page, 0);
    if (s.diagnostics && m.load32(page + oHashID) != s.page_hash) {
        s.page_hash = m.load32(page + oHashID);
        std::cerr << "[menu-cursor] focused page " << psprecomp::hex32(s.page_hash) << " selectable widgets " << selectable << "\n";
    }
    if (selectable == 0u) { inactive(); return; }

    if (!s.presses.empty()) { vcs::display_window_set_menu_buttons(s.presses.front()); s.presses.pop_front(); }
    else vcs::display_window_set_menu_buttons(0u);
    const vcs::MenuCursorState cursor = vcs::display_window_menu_cursor();
    if (!cursor.available) { vcs::display_window_set_menu_cursor(true, false); s.left_was_down = cursor.left; return; }
    if (cursor.x != s.last_x || cursor.y != s.last_y) { s.last_x = cursor.x; s.last_y = cursor.y; s.moved_recently = 15; }
    else if (s.moved_recently > 0) --s.moved_recently;
    const bool left_pressed = cursor.left && !s.left_was_down;
    s.left_was_down = cursor.left;

    // Button prompts come first: clicking one presses its button and leaves the
    // selection where it is (the spawn point stays chosen for Customization).
    if (const std::uint32_t prompt = prompt_at(m, page, cursor.x, cursor.y)) {
        vcs::display_window_set_menu_cursor(true, true, 0u);
        if (left_pressed && s.presses.empty() && m.load32(page + oPageState) == kPageStateActive) {
            queue_press(s.presses, prompt);
            if (s.diagnostics) std::cerr << "[menu-cursor] prompt click button " << psprecomp::hex32(prompt) << "\n";
        }
        return;
    }
    // A widget whose drawn images are under the pointer wins over one whose
    // (often wider) label text merely reaches there.
    std::uint32_t hit = find_selectable_widget_at(m, page, cursor.x, cursor.y, 0, true);
    if (hit == 0u) hit = find_selectable_widget_at(m, page, cursor.x, cursor.y, 0, false);
    const std::uint32_t hit_type = hit != 0u ? m.load32(hit + oType) : 0u;
    const bool hit_slider = hit_type == kTypeSlider;
    const int row = hit_type == kTypeTextListBox ? list_row_at(m, hit, cursor.x, cursor.y) : -1;
    // What a left click sends: accept, nothing (slider drags, list space without
    // a row), or the numeric's left/right step.
    std::uint32_t click = kButtonAccept;
    if (hit_slider || (hit_type == kTypeTextListBox && row < 0)) click = 0u;
    else if (hit_type == kTypeNumeric) {
        // Left/right half of the arrow box, played as Accept, arrow, Accept.
        const std::uint32_t step = numeric_click(m, hit, cursor.x);
        if (step != kButtonAccept) {
            click = 0u;
            if (left_pressed && s.presses.empty() && m.load32(page + oActiveWidget) == hit)
                for (const std::uint32_t b : {kButtonAccept, step, kButtonAccept}) queue_press(s.presses, b);
        }
    }
    // An accept click is played as a held press after the widget under the
    // pointer has been made the page's active one (below), so the game never
    // accepts whatever was highlighted before the click.
    const bool queue_accept = click == kButtonAccept;
    vcs::display_window_set_menu_cursor(true, hit != 0u, queue_accept ? 0u : click);
    const bool page_active = m.load32(page + oPageState) == kPageStateActive;
    // Scroll bar: a click on the track jumps there, holding drags the thumb.
    if (!cursor.left) s.scroll_list = 0u;
    else if (left_pressed && page_active) s.scroll_list = scroll_bar_at(m, page, cursor.x, cursor.y, s.track_top, s.track_height);
    if (s.scroll_list != 0u && page_active && s.track_height > 0.f) {
        const int count = static_cast<int>(m.load32(s.scroll_list + oListCount));
        const float fraction = std::clamp((cursor.y - s.track_top) / s.track_height, 0.f, 1.f);
        const int entry = static_cast<int>(std::lround(fraction * static_cast<float>(std::max(0, count - 1))));
        if (static_cast<int>(m.load32(s.scroll_list + oListSelected)) != entry) {
            list_show(m, s.scroll_list, entry, static_cast<int>(std::lround(load_float(m, s.scroll_list + oListOffset))));
            if (s.diagnostics) std::cerr << "[menu-cursor] scroll bar drag entry " << entry << "\n";
        }
    }
    // Wheel: over a list the rows scroll one per notch and the highlight stays on
    // the row under the pointer; elsewhere a notch is an up/down press.
    if (cursor.wheel != 0 && page_active) {
        if (hit_type == kTypeTextListBox) {
            const float offset_before = load_float(m, hit + oListOffset), target_before = load_float(m, hit + oListTargetOffset);
            const int offset = static_cast<int>(std::lround(offset_before));
            const int shown = static_cast<int>(m.load32(hit + oListMaxDisplayed));
            const int count = static_cast<int>(m.load32(hit + oListCount));
            const int new_offset = std::clamp(offset - cursor.wheel, 0, std::max(0, count - shown));
            const int under = row >= 0 ? row - offset : -1;  // visible slot under the pointer
            const int selected = static_cast<int>(m.load32(hit + oListSelected));
            const int entry = under >= 0 ? new_offset + under : std::clamp(selected - cursor.wheel, new_offset, new_offset + shown - 1);
            list_show(m, hit, entry, new_offset);
            if (s.diagnostics) std::cerr << "[menu-cursor] wheel " << cursor.wheel << " row " << row << " offset " << offset_before << "/" << target_before << " list offset " << new_offset << " entry " << entry << "\n";
        } else {
            for (int i = 0; i < std::abs(cursor.wheel) && s.presses.size() < 64u; ++i) queue_press(s.presses, cursor.wheel > 0 ? 0x10u : 0x40u);
        }
    }
    // List rows follow the cursor while it moves (and on a click), as in the engine.
    if (row >= 0 && (s.moved_recently > 0 || left_pressed) && m.load32(page + oPageState) == kPageStateActive &&
        static_cast<int>(m.load32(hit + oListSelected)) != row) {
        m.store32(hit + oListSelected, static_cast<std::uint32_t>(row));
        if (s.diagnostics) std::cerr << "[menu-cursor] list " << psprecomp::hex32(m.load32(hit + oHashID)) << " row " << row << "\n";
    }
    // Slider drag: starts with a click on a slider, follows the cursor while held.
    if (!cursor.left) s.dragging = 0u;
    else if (left_pressed && hit_slider) s.dragging = hit;
    if (s.dragging != 0u && m.load32(page + oPageState) == kPageStateActive) {
        if (m.load32(page + oActiveWidget) == s.dragging) drag_slider(rt, ctx, s.dragging, cursor.x, s.diagnostics);
        else s.dragging = 0u;
    }
    if (hit == 0u || m.load32(page + oPageState) != kPageStateActive) return;
    if (queue_accept && left_pressed && s.presses.empty()) queue_press(s.presses, kButtonAccept);
    // Asura uses the cursor position while it is moving (or on a click), so a
    // resting mouse does not fight pad/keyboard navigation, and does not change
    // the selection while the button stays held (slider drags).
    if (!(s.moved_recently > 0 || left_pressed)) return;
    if (cursor.left && !left_pressed) return;

    const std::uint32_t hit_hash = m.load32(hit + oHashID);
    const std::uint32_t active_hash = m.load32(page + oActiveWidgetHash);
    if (hit_hash == active_hash) return;
    const std::uint32_t page_hash = m.load32(page + oHashID);
    // Notify the new and old widgets (the engine's cursor path: ROLL_IN to the
    // widget under the cursor, ROLL_OUT to the previous one), then make it the
    // page's active widget so button presses reach it.
    pc_settings::call_guest_routine(rt, ctx, kPostMessage, {hit_hash, page_hash, kMsgOnRollIn, 0u, 0u});
    if (active_hash != 0u)
        pc_settings::call_guest_routine(rt, ctx, kPostMessage, {active_hash, page_hash, kMsgOnRollOut, 0u, 0u});
    m.store32(page + oActiveWidget, hit);
    m.store32(page + oActiveWidgetHash, hit_hash);
    if (s.diagnostics)
        std::cerr << "[menu-cursor] page " << psprecomp::hex32(page_hash) << " cursor " << cursor.x << ',' << cursor.y
                  << " selects widget " << psprecomp::hex32(hit_hash) << " (was " << psprecomp::hex32(active_hash) << ")\n";
}
}  // namespace renegade::menu_cursor
