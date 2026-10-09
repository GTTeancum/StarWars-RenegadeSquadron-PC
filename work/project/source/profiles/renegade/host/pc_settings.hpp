#pragma once
// PC settings exposed to the game's own menus.
//
// Asura PC keeps every user option as a command-console variable
// (Asura_CommandConsole::AddVar) and the GUIMenu widgets bind to those by name
// (slider/checkbox/numeric console_var, button commands, condition texts).
// Renegade's PSP build ships the same console, so the PC options are
// registered through the game's AddVar/AddCmd routines as "PC.*" variables and
// "PC_*" commands, and the extra menu pages in mods\files bind to them exactly
// like the shipped Audio/Controls pages bind to "BFF.*".
//
// The variables live in guest memory; the host polls them once per vblank and
// applies changes (window, renderer, input) and saves RenegadeSquadron.ini.
#include "psprecomp/runtime.hpp"
#include <cstdint>
#include <filesystem>

namespace renegade::pc_settings {
// Called from the sceIoOpen HLE: registers the console variables/commands the
// first time the game opens a menu file (the console exists by then).
void ensure_registered(psprecomp::Runtime &rt, psprecomp::AllegrexContext &caller, const std::string &psp_path);
// Once per vblank: applies changed values and writes the settings file.
void poll(psprecomp::Runtime &rt, psprecomp::AllegrexContext &ctx);
// Settings file written when a value changes (installed layout only).
void set_settings_file(const std::filesystem::path &ini);
}

// Host hooks implemented in psp_services.cpp for the settings module.
namespace vcs {
// Carves a block out of the guest partition arena (same allocator as
// sceKernelAllocPartitionMemory). Returns 0 on failure.
std::uint32_t pc_settings_allocate_block(psprecomp::Runtime &rt, std::uint32_t size, const char *name);
// Replaces the game's frame-rate cap (Asura_Timers s_fMaxFrameRate).
void pc_settings_set_frame_rate_cap(float cap);
}
