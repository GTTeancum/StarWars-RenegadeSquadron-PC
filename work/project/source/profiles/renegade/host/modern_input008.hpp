#pragma once
#include <array>
#include <cstdint>
#include <optional>
namespace psprecomp { class Runtime; struct AllegrexContext; }
namespace renegade::input008 {
// SDL semantic button order, not device-specific joystick indices.
enum Button: unsigned { A=0,B=1,X=2,Y=3,Back=4,Guide=5,Start=6,
 LeftStick=7,RightStick=8,LeftShoulder=9,RightShoulder=10,
 Up=11,Down=12,Left=13,Right=14 };
constexpr std::uint32_t bit(Button b){return 1u<<b;}
struct RawPad {
 bool connected{},enabled{};
 std::int16_t lx{},ly{},rx{},ry{},lt{},rt{};
 std::uint32_t buttons{};
};
struct Config {
 float left_deadzone=7849.f/32767.f,right_deadzone=8689.f/32767.f;
 float look_x=1.f,look_y=1.f,curve=1.f,trigger_threshold=30.f/255.f;
 bool invert_y{};
};
struct Frame {
 bool active{},enabled{};
 float move_x{},move_y{},look_x{},look_y{},left_trigger{},right_trigger{};
 std::uint32_t buttons{};
};
Config config_from_environment();
bool modern_enabled();
Frame normalize(const RawPad&,const Config&);
RawPad live_gamepad(); // production SDL high-level game-controller sampler
void frame_tick(std::uint64_t vblank);
Frame current();
float trigger_threshold();
std::uint64_t frame_number();
bool pending_action(unsigned action); // consume a per-action, latched rising edge
void quarantine_held_actions009(); // input ownership transition, no guest state writes
void reset();
void reset(const Config&); // deterministic test config
void accept_sample(std::uint64_t,const RawPad&); // same path for live/diagnostic/test input
void action_getter(psprecomp::Runtime&,psprecomp::AllegrexContext&);
}
namespace renegade {void install_control_bridge008(psprecomp::Runtime&);}
