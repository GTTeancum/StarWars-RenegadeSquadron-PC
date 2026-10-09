#include "pc_settings.hpp"
#include "display_window.hpp"
#include "ge_gpu_backend.hpp"
#include "ge_renderer.hpp"
#include "modern_input008.hpp"
#include "psprecomp/common.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cctype>
#include <cstdio>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

namespace renegade::pc_settings {
namespace {
// Game console registration routines (ULUS10292; the AddVar/AddCmd wrappers
// the game itself uses for BFF.* variables and FE_* commands).
constexpr std::uint32_t kAddVarBool = 0x088977A0u;   // (name, bool*, remove, restr)
constexpr std::uint32_t kAddVarInt = 0x08897814u;    // (name, int*, lo, hi, remove, restr)
constexpr std::uint32_t kAddVarFloat = 0x08897854u;  // (name, float*, f12 lo, f13 hi, remove, restr)
constexpr std::uint32_t kAddCmd = 0x08897664u;       // (name, void (*fn)(), remove, 0)
// Asura_CommandConsole::REMOVE_AT_SHUTDOWN. The default (1, REMOVE_AT_RESET)
// is cleared when the console resets on entering the front end.
constexpr std::uint32_t kRemoveAtShutdown = 0u;

// Window sizes offered by the Video Options page (PC.Resolution index; the
// labels are text ids PC_RES_0.. in the menu text). The last entry is the
// desktop size.
struct Resolution { int width, height; };
constexpr std::array<Resolution, 8> kResolutions{{
    {1280, 720}, {1366, 768}, {1600, 900}, {1920, 1080}, {2560, 1440}, {3440, 1440}, {3840, 2160}, {0, 0}}};

enum Slot : std::uint32_t {
    kResolution, kFullscreen, kFrameRateCap, kPerPixelLighting, kShadows, kBloom, kSmoothFog,
    kLookX, kLookY, kInvertY, kLeftDeadzone, kRightDeadzone, kControlScheme, kMouseSensitivity, kMouseInvertY, kSlotCount
};
enum Command : std::uint32_t { kQuitGame, kResolutionNext, kResolutionPrev, kControlSchemeNext, kCommandCount };

struct Guest {
    std::uint32_t block{};       // partition block (values, strings, stub addresses, stack)
    std::uint32_t stack_top{};
    std::uint32_t sentinel{};
    std::uint32_t strings{};     // next free byte in the string area
    bool registered{};
    bool failed{};
    bool trigger{};              // a menu file was opened; register at the next main-thread vblank
    std::string trigger_path;
};
Guest g;
constexpr std::uint32_t kBlockSize = 0x10000u;
constexpr std::uint32_t kValues = 0x0u;        // 4 bytes per slot
constexpr std::uint32_t kStrings = 0x100u;     // UTF-16 names/descriptions
constexpr std::uint32_t kStubs = 0x1000u;      // host functions registered at these addresses
constexpr std::uint32_t kStubStride = 0x10u;

// Host-side copy of the values (what has been applied) and pending commands.
std::array<std::uint32_t, kSlotCount> applied{};
std::array<bool, kCommandCount> command_pending{};
bool sentinel_hit = false;
std::filesystem::path settings_file;
int save_countdown = 0;

std::uint32_t slot_address(Slot slot) { return g.block + kValues + 4u * slot; }

float env_float(const char *name, float fallback) {
    const char *text = std::getenv(name);
    if (text == nullptr || *text == '\0') return fallback;
    char *end = nullptr;
    const float value = std::strtof(text, &end);
    return end != text && std::isfinite(value) ? value : fallback;
}
bool env_flag(const char *name, bool fallback) {
    const char *text = std::getenv(name);
    if (text == nullptr || *text == '\0') return fallback;
    return std::strcmp(text, "0") != 0;
}
int resolution_index_from_env() {
    const char *text = std::getenv("RENEGADE_OUTPUT_RESOLUTION");
    if (text == nullptr) return 0;
    int w = 0, h = 0;
    if (std::sscanf(text, "%dx%d", &w, &h) != 2) return 0;
    for (std::size_t i = 0; i < kResolutions.size(); ++i)
        if (kResolutions[i].width == w && kResolutions[i].height == h) return static_cast<int>(i);
    return 0;
}

std::uint32_t put_wide_string(psprecomp::Runtime &rt, const char *text) {
    const std::uint32_t address = g.strings;
    for (const char *c = text; ; ++c) {
        rt.memory().store16(g.strings, static_cast<std::uint16_t>(static_cast<unsigned char>(*c)));
        g.strings += 2u;
        if (*c == '\0') break;
    }
    g.strings = (g.strings + 3u) & ~3u;
    return address;
}

// Runs one guest routine to completion on a private stack. The sentinel
// return address is a host function, so the loop ends when the routine
// returns. Direct chaining inside generated units is unaffected; any import
// the routine calls runs through its wrapper like an ordinary dispatch.
bool call_guest(psprecomp::Runtime &rt, const psprecomp::AllegrexContext &caller, std::uint32_t address,
                std::initializer_list<std::uint32_t> args, float f12 = 0.0f, float f13 = 0.0f) {
    psprecomp::AllegrexContext ctx{};
    ctx.gpr[26] = caller.gpr[26];
    ctx.gpr[27] = caller.gpr[27];
    ctx.gpr[28] = caller.gpr[28];
    ctx.gpr[29] = g.stack_top;
    ctx.gpr[31] = g.sentinel;
    ctx.pc = address;
    std::uint32_t reg = 4u;
    for (const std::uint32_t arg : args) ctx.gpr[reg++] = arg;
    ctx.fpr[12] = f12;
    ctx.fpr[13] = f13;
    sentinel_hit = false;
    for (unsigned step = 0; step < 4'000'000u; ++step) {
        // One registered unit per step; the routine's own calls and returns
        // leave ctx.pc at the next address to run.
        if (!rt.invoke_isolated_aot(ctx.pc, ctx)) {
            std::cerr << "[pc-settings] no function at " << psprecomp::hex32(ctx.pc) << " while calling "
                      << psprecomp::hex32(address) << "\n";
            return false;
        }
        if (sentinel_hit) return ctx.gpr[2] != 0u;  // the console routines return true on success
        if (rt.stopped()) return false;
    }
    std::cerr << "[pc-settings] guest call " << psprecomp::hex32(address) << " did not return\n";
    return false;
}

void sentinel_function(psprecomp::Runtime &, psprecomp::AllegrexContext &) { sentinel_hit = true; }

// Console command callbacks: the game jumps here through its command table.
template <Command C>
void command_function(psprecomp::Runtime &rt, psprecomp::AllegrexContext &ctx) {
    if constexpr (C == kResolutionNext || C == kResolutionPrev) {
        const std::uint32_t address = slot_address(kResolution);
        const int count = static_cast<int>(kResolutions.size());
        int index = static_cast<int>(rt.memory().load32(address));
        index = (index + (C == kResolutionNext ? 1 : count - 1)) % count;
        rt.memory().store32(address, static_cast<std::uint32_t>(index));
    } else if constexpr (C == kControlSchemeNext) {
        const std::uint32_t address = slot_address(kControlScheme);
        rt.memory().store32(address, rt.memory().load32(address) ? 0u : 1u);
    } else {
        command_pending[C] = true;
    }
    ctx.gpr[2] = 0u;
    ctx.pc = ctx.gpr[31];
}

bool add_bool(psprecomp::Runtime &rt, const psprecomp::AllegrexContext &caller, const char *name, Slot slot, bool value) {
    rt.memory().store32(slot_address(slot), value ? 1u : 0u);
    applied[slot] = value ? 1u : 0u;
    return call_guest(rt, caller, kAddVarBool, {put_wide_string(rt, name), slot_address(slot), kRemoveAtShutdown, 0u});
}
bool add_int(psprecomp::Runtime &rt, const psprecomp::AllegrexContext &caller, const char *name, Slot slot, int value, int lo, int hi) {
    rt.memory().store32(slot_address(slot), static_cast<std::uint32_t>(value));
    applied[slot] = static_cast<std::uint32_t>(value);
    return call_guest(rt, caller, kAddVarInt, {put_wide_string(rt, name), slot_address(slot), static_cast<std::uint32_t>(lo),
                                               static_cast<std::uint32_t>(hi), kRemoveAtShutdown, 0u});
}
bool add_float(psprecomp::Runtime &rt, const psprecomp::AllegrexContext &caller, const char *name, Slot slot, float value, float lo, float hi) {
    rt.memory().store32(slot_address(slot), std::bit_cast<std::uint32_t>(value));
    applied[slot] = std::bit_cast<std::uint32_t>(value);
    return call_guest(rt, caller, kAddVarFloat, {put_wide_string(rt, name), slot_address(slot), kRemoveAtShutdown, 0u}, lo, hi);
}
bool add_command(psprecomp::Runtime &rt, const psprecomp::AllegrexContext &caller, const char *name, Command command,
                 psprecomp::Runtime::RecompiledFunction fn) {
    const std::uint32_t address = g.block + kStubs + kStubStride * (1u + command);
    rt.register_function(address, fn, std::string("pc_settings::") + name);
    return call_guest(rt, caller, kAddCmd, {put_wide_string(rt, name), address, kRemoveAtShutdown, 0u});
}

float slot_float(psprecomp::Runtime &rt, Slot slot) { return std::bit_cast<float>(rt.memory().load32(slot_address(slot))); }
bool slot_bool(psprecomp::Runtime &rt, Slot slot) { return rt.memory().load8(slot_address(slot)) != 0u; }
int slot_int(psprecomp::Runtime &rt, Slot slot) { return static_cast<int>(rt.memory().load32(slot_address(slot))); }

std::string resolution_text(int index) {
    index = std::clamp(index, 0, static_cast<int>(kResolutions.size()) - 1);
    const Resolution r = kResolutions[static_cast<std::size_t>(index)];
    if (r.width == 0) return "desktop";
    return std::to_string(r.width) + "x" + std::to_string(r.height);
}

// Rewrites the managed keys in RenegadeSquadron.ini, keeping everything else.
void save_settings(psprecomp::Runtime &rt) {
    if (settings_file.empty()) return;
    const auto on_off = [](bool v) { return std::string(v ? "true" : "false"); };
    const auto number = [](float v) { std::ostringstream s; s.precision(4); s << v; return s.str(); };
    const std::vector<std::pair<std::string, std::vector<std::pair<std::string, std::string>>>> sections{
        {"Graphics", {{"WindowSize", resolution_text(slot_int(rt, kResolution))},
                      {"Fullscreen", on_off(slot_bool(rt, kFullscreen))},
                      {"FrameRateCap", std::to_string(static_cast<int>(std::lround(slot_float(rt, kFrameRateCap))))},
                      {"PerPixelLighting", on_off(slot_bool(rt, kPerPixelLighting))},
                      {"Shadows", on_off(slot_bool(rt, kShadows))},
                      {"Bloom", on_off(slot_bool(rt, kBloom))},
                      {"SmoothFog", on_off(slot_bool(rt, kSmoothFog))}}},
        {"Controller", {{"Scheme", slot_int(rt, kControlScheme) ? "legacy" : "modern"},
                        {"LookSensitivityX", number(slot_float(rt, kLookX))},
                        {"LookSensitivityY", number(slot_float(rt, kLookY))},
                        {"InvertY", on_off(slot_bool(rt, kInvertY))},
                        {"LeftDeadzone", number(slot_float(rt, kLeftDeadzone))},
                        {"RightDeadzone", number(slot_float(rt, kRightDeadzone))}}},
        {"Mouse", {{"Sensitivity", number(slot_float(rt, kMouseSensitivity))},
                   {"InvertY", on_off(slot_bool(rt, kMouseInvertY))}}}};
    std::vector<std::string> lines;
    if (std::ifstream in{settings_file}) {
        std::string line;
        while (std::getline(in, line)) {
            if (!line.empty() && line.back() == '\r') line.pop_back();
            lines.push_back(line);
        }
    }
    const auto lower = [](std::string s) { for (char &c : s) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c))); return s; };
    const auto trim = [](const std::string &s) {
        const auto first = s.find_first_not_of(" \t");
        if (first == std::string::npos) return std::string();
        return s.substr(first, s.find_last_not_of(" \t") - first + 1u);
    };
    for (const auto &[section, keys] : sections) {
        std::size_t begin = lines.size(), end = lines.size();
        for (std::size_t i = 0; i < lines.size(); ++i) {
            const std::string t = trim(lines[i]);
            if (t.size() >= 2u && t.front() == '[' && t.back() == ']') {
                if (begin != lines.size()) { end = i; break; }
                if (lower(t.substr(1, t.size() - 2)) == lower(section)) begin = i + 1u;
            }
        }
        if (begin == lines.size()) {
            if (!lines.empty() && !trim(lines.back()).empty()) lines.emplace_back();
            lines.push_back("[" + section + "]");
            begin = end = lines.size();
        }
        for (const auto &[key, value] : keys) {
            bool found = false;
            for (std::size_t i = begin; i < end; ++i) {
                const std::string t = lines[i];
                const auto eq = t.find('=');
                if (eq == std::string::npos) continue;
                if (lower(trim(t.substr(0, eq))) != lower(key)) continue;
                const auto comment = t.find_first_of(";#", eq);
                lines[i] = key + "=" + value + (comment != std::string::npos ? "  " + t.substr(comment) : "");
                found = true;
                break;
            }
            if (!found) {
                std::size_t at = end;  // before the blank lines that separate sections
                while (at > begin && trim(lines[at - 1u]).empty()) --at;
                lines.insert(lines.begin() + static_cast<std::ptrdiff_t>(at), key + "=" + value);
                ++end;
            }
        }
    }
    std::ofstream out(settings_file, std::ios::trunc);
    for (const std::string &line : lines) out << line << "\n";
    std::cerr << "[pc-settings] saved " << settings_file.string() << "\n";
}

void apply_video(psprecomp::Runtime &rt) {
    const int index = std::clamp(slot_int(rt, kResolution), 0, static_cast<int>(kResolutions.size()) - 1);
    const Resolution r = kResolutions[static_cast<std::size_t>(index)];
    vcs::display_window_apply_video(r.width, r.height, slot_bool(rt, kFullscreen));
}

void apply_input(psprecomp::Runtime &rt) {
    input008::Config c = input008::config();
    c.look_x = std::clamp(slot_float(rt, kLookX), 0.05f, 4.0f);
    c.look_y = std::clamp(slot_float(rt, kLookY), 0.05f, 4.0f);
    c.invert_y = slot_bool(rt, kInvertY);
    c.left_deadzone = std::clamp(slot_float(rt, kLeftDeadzone), 0.0f, 0.9f);
    c.right_deadzone = std::clamp(slot_float(rt, kRightDeadzone), 0.0f, 0.9f);
    c.mouse_sensitivity = std::clamp(slot_float(rt, kMouseSensitivity), 0.05f, 10.0f);
    c.mouse_invert_y = slot_bool(rt, kMouseInvertY);
    input008::set_config(c);
}
}  // namespace

void set_settings_file(const std::filesystem::path &ini) { settings_file = ini; }

void ensure_registered(psprecomp::Runtime &, psprecomp::AllegrexContext &, const std::string &psp_path) {
    if (g.registered || g.failed || g.trigger) return;
    // The GUI system opens its menu files well after the console is up. The
    // open itself runs on the loader thread, whose allocations go to a scratch
    // heap that is reclaimed after the load, so only note it here; the
    // registration runs on the main thread at its next vblank wait.
    std::string upper = psp_path;
    for (char &c : upper) c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
    if (upper.find("GUIMENU") == std::string::npos || upper.find(".GUI") == std::string::npos) return;
    g.trigger = true;
    g.trigger_path = psp_path;
}

namespace {
void register_now(psprecomp::Runtime &rt, psprecomp::AllegrexContext &caller) {
    g.registered = true;
    g.block = vcs::pc_settings_allocate_block(rt, kBlockSize, "PCSettings");
    if (g.block == 0u) { g.failed = true; std::cerr << "[pc-settings] guest block allocation failed\n"; return; }
    g.stack_top = g.block + kBlockSize - 0x40u;
    g.strings = g.block + kStrings;
    g.sentinel = g.block + kStubs;
    rt.register_function(g.sentinel, sentinel_function, "pc_settings::return");

    const char *controls = std::getenv("RENEGADE_CONTROLS");
    const int scheme = controls != nullptr && std::strcmp(controls, "legacy") == 0 ? 1 : 0;
    const char *fog = std::getenv("RENEGADE_FOG_CURVE");
    const input008::Config input = input008::config();
    bool ok = true;
    ok &= add_int(rt, caller, "PC.Resolution", kResolution, resolution_index_from_env(), 0, static_cast<int>(kResolutions.size()) - 1);
    ok &= add_bool(rt, caller, "PC.Fullscreen", kFullscreen, env_flag("RENEGADE_FULLSCREEN", false));
    ok &= add_float(rt, caller, "PC.FrameRateCap", kFrameRateCap, env_float("RENEGADE_FRAME_RATE_CAP", 60.0f), 30.0f, 240.0f);
    ok &= add_bool(rt, caller, "PC.PerPixelLighting", kPerPixelLighting, env_flag("RENEGADE_PER_PIXEL_LIGHTING", true));
    ok &= add_bool(rt, caller, "PC.Shadows", kShadows, env_flag("RENEGADE_SHADOWS", true));
    ok &= add_bool(rt, caller, "PC.Bloom", kBloom, env_flag("RENEGADE_BLOOM", true));
    ok &= add_bool(rt, caller, "PC.SmoothFog", kSmoothFog, fog != nullptr && std::strcmp(fog, "smooth") == 0);
    ok &= add_float(rt, caller, "PC.LookSensitivityX", kLookX, input.look_x, 0.1f, 2.0f);
    ok &= add_float(rt, caller, "PC.LookSensitivityY", kLookY, input.look_y, 0.1f, 2.0f);
    ok &= add_bool(rt, caller, "PC.InvertY", kInvertY, input.invert_y);
    ok &= add_float(rt, caller, "PC.LeftDeadzone", kLeftDeadzone, input.left_deadzone, 0.0f, 0.5f);
    ok &= add_float(rt, caller, "PC.RightDeadzone", kRightDeadzone, input.right_deadzone, 0.0f, 0.5f);
    ok &= add_int(rt, caller, "PC.ControlScheme", kControlScheme, scheme, 0, 1);
    ok &= add_float(rt, caller, "PC.MouseSensitivity", kMouseSensitivity, input.mouse_sensitivity, 0.1f, 3.0f);
    ok &= add_bool(rt, caller, "PC.MouseInvertY", kMouseInvertY, input.mouse_invert_y);
    ok &= add_command(rt, caller, "PC_QuitGame", kQuitGame, command_function<kQuitGame>);
    ok &= add_command(rt, caller, "PC_ResolutionNext", kResolutionNext, command_function<kResolutionNext>);
    ok &= add_command(rt, caller, "PC_ResolutionPrev", kResolutionPrev, command_function<kResolutionPrev>);
    ok &= add_command(rt, caller, "PC_ControlSchemeNext", kControlSchemeNext, command_function<kControlSchemeNext>);
    std::cerr << "[pc-settings] console variables registered at " << psprecomp::hex32(g.block)
              << (ok ? "" : " (some registrations failed)") << "\n";
}

}  // namespace

void poll(psprecomp::Runtime &rt, psprecomp::AllegrexContext &ctx) {
    // Register as soon as the console exists (Asura_CommandConsole_VarRepository
    // s_xVarTree root, static at 0x08B2A72C), from the main thread's vblank
    // wait so the entries are allocated from the same heap as the game's own.
    constexpr std::uint32_t kVarTreeRoot = 0x08B2A72Cu;
    if (!g.registered && !g.failed && rt.memory().load32(kVarTreeRoot) != 0u) {
        register_now(rt, ctx);
    }
    if (!g.registered || g.failed) return;
    if (command_pending[kQuitGame]) {
        command_pending[kQuitGame] = false;
        vcs::display_window_request_close();
    }
    bool changed = false;
    const auto take = [&](Slot slot) {
        const std::uint32_t value = slot == kFullscreen || slot == kPerPixelLighting || slot == kShadows || slot == kBloom ||
                                            slot == kSmoothFog || slot == kInvertY || slot == kMouseInvertY
                                        ? (rt.memory().load8(slot_address(slot)) != 0u ? 1u : 0u)
                                        : rt.memory().load32(slot_address(slot));
        if (value == applied[slot]) return false;
        applied[slot] = value;
        changed = true;
        return true;
    };
    bool video = false, input = false;
    video |= take(kResolution);
    video |= take(kFullscreen);
    if (take(kFrameRateCap)) vcs::pc_settings_set_frame_rate_cap(std::clamp(slot_float(rt, kFrameRateCap), 30.0f, 240.0f));
    if (take(kPerPixelLighting)) vcs::ge_set_per_pixel_lighting(slot_bool(rt, kPerPixelLighting));
    if (take(kShadows)) {
        vcs::ge_gpu_backend_set_shadows(slot_bool(rt, kShadows));
        vcs::ge_set_receive_shadows(slot_bool(rt, kShadows));
    }
    if (take(kBloom)) vcs::ge_gpu_backend_set_bloom(slot_bool(rt, kBloom));
    if (take(kSmoothFog)) vcs::ge_gpu_backend_set_smooth_fog(slot_bool(rt, kSmoothFog));
    input |= take(kLookX);
    input |= take(kLookY);
    input |= take(kInvertY);
    input |= take(kLeftDeadzone);
    input |= take(kRightDeadzone);
    input |= take(kMouseSensitivity);
    input |= take(kMouseInvertY);
    if (take(kControlScheme)) {
#if defined(_WIN32)
        _putenv_s("RENEGADE_CONTROLS", slot_int(rt, kControlScheme) ? "legacy" : "modern");
#else
        setenv("RENEGADE_CONTROLS", slot_int(rt, kControlScheme) ? "legacy" : "modern", 1);
#endif
    }
    if (video) apply_video(rt);
    if (input) apply_input(rt);
    if (changed) save_countdown = 30;  // sliders drag through many values; write once they settle
    if (save_countdown > 0 && --save_countdown == 0) save_settings(rt);
}
}  // namespace renegade::pc_settings
