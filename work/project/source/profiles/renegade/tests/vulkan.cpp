#include "ge_gpu_backend.hpp"
#include "vcs_config.hpp"
#include <array>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <windows.h>
namespace {
void check(bool ok, const char *message) {
  if (!ok)
    throw std::runtime_error(message);
}
std::array<vcs::GeGpuVertex, 6> rect(float x, float y, float w, float h,
                                     unsigned color, float z = 0) {
  std::array<vcs::GeGpuVertex, 6> v{};
  const float xy[6][2] = {{0, 0}, {1, 0}, {0, 1}, {1, 0}, {1, 1}, {0, 1}};
  for (unsigned n = 0; n < 6; ++n) {
    v[n].x = x + xy[n][0] * w;
    v[n].y = y + xy[n][1] * h;
    v[n].z = z;
    v[n].u = xy[n][0] * 2;
    v[n].v = xy[n][1] * 2;
    v[n].rgba = color;
  }
  return v;
}
void pixel(unsigned x, unsigned y, unsigned color, unsigned tolerance = 1) {
  auto p = vcs::ge_gpu_backend_game_frame_rgba();
  auto r = vcs::ge_gpu_backend_report();
  for (unsigned c = 0; c < 4; ++c) {
    unsigned actual = std::to_integer<unsigned>(
                 p[(y * r.offscreen_width + x) * 4 + c]),
             expected = (color >> (8 * c)) & 255;
    if (std::abs(int(actual) - int(expected)) > int(tolerance))
      throw std::runtime_error(
          "Pixel " + std::to_string(x) + "," + std::to_string(y) + " channel " +
          std::to_string(c) + " expected " + std::to_string(expected) +
          " got " + std::to_string(actual));
  }
}
} // namespace
int main(int argc, char **argv) {
  try {
    auto dir = std::filesystem::current_path();
    std::ofstream(dir / "VulkanTest.ini")
        << "[Rendering]\nBackend=Vulkan\nInternalResolutionMode=PSP\nMSAA="
        << (argc > 1 ? argv[1] : "4") << "\n";
    _putenv_s("PSPRECOMP_CONFIG", (dir / "VulkanTest.ini").string().c_str());
    vcs::initialize_vcs_configuration(dir);
    std::string error;
    check(vcs::initialize_ge_gpu_backend(error), error.c_str());
    check(vcs::ge_gpu_backend_report().active == vcs::GeGpuBackendKind::Vulkan,
          "Vulkan selection silently fell back");
    std::cout << "Adapter: " << vcs::ge_gpu_backend_report().message << '\n';
    // This is an invisible window owned by this test process. It receives no
    // input and is never shown or activated; it only supplies a Vulkan surface.
    HWND hidden = nullptr;
    if (argc > 2 && std::string(argv[2]) == "present") {
      hidden = CreateWindowExW(0, L"STATIC", L"Renegade Vulkan surface test",
                               WS_OVERLAPPEDWINDOW, 0, 0, 800, 600, nullptr,
                               nullptr, GetModuleHandleW(nullptr), nullptr);
      check(hidden != nullptr, "Create test surface window");
      vcs::ge_gpu_backend_set_native_window(hidden);
      check(vcs::ge_gpu_backend_presents_directly(),
            "Native Vulkan swapchain initialization");
    }
    vcs::GeGpuDrawDescriptor d{};
    d.framebuffer_address = 0x04000000;
    d.framebuffer_format = 3;
    d.framebuffer_stride = 512;
    d.through = true;
    vcs::ge_gpu_backend_set_display_framebuffer(d.framebuffer_address);
    vcs::ge_gpu_backend_accumulate_color_triangles(
        d, rect(0, 0, 480, 272, 0xff302010));
    auto depth = d;
    depth.depth_test_enabled = depth.depth_write_enabled = true;
    depth.depth_function = 4;
    vcs::ge_gpu_backend_accumulate_color_triangles(
        depth, rect(20, 20, 100, 100, 0xff0000ff, 20000));
    vcs::ge_gpu_backend_accumulate_color_triangles(
        depth, rect(40, 40, 100, 100, 0xff00ff00, 40000));
    auto sc = d;
    sc.scissor_x0 = 160;
    sc.scissor_y0 = 30;
    sc.scissor_x1 = 199;
    sc.scissor_y1 = 69;
    vcs::ge_gpu_backend_accumulate_color_triangles(
        sc, rect(140, 10, 100, 100, 0xff00ffff));
    auto tex = d;
    tex.texture_enabled = true;
    tex.texture_address = 0x08800000;
    tex.texture_content_signature = 1234;
    tex.texture_width = tex.texture_height = 2;
    tex.texture_function = 3;
    tex.texture_use_alpha = true;
    tex.texture_clamp_u = tex.texture_clamp_v = true;
    unsigned colors[] = {0xff0000ff, 0xff00ff00, 0xffff0000, 0xffffffff};
    check(vcs::ge_gpu_backend_upload_decoded_texture(
              tex, 2, 2,
              {reinterpret_cast<const std::byte *>(colors), sizeof(colors)}),
          "Texture upload");
    auto checked_texture = tex;
    checked_texture.texture_content_signature = 0;
    check(!vcs::ge_gpu_backend_texture_needed(checked_texture),
          "Omitted per-frame signature must reuse the texture");
    checked_texture.texture_content_signature = 4321;
    check(vcs::ge_gpu_backend_texture_needed(checked_texture),
          "Changed source checksum must request an upload");
    vcs::ge_gpu_backend_accumulate_color_triangles(
        tex, rect(260, 20, 100, 100, 0xffffffff));
    auto alpha = d;
    alpha.alpha_test_enabled = true;
    alpha.alpha_function = 6;
    alpha.alpha_reference = 128;
    alpha.alpha_mask = 255;
    vcs::ge_gpu_backend_accumulate_color_triangles(
        alpha, rect(20, 160, 60, 60, 0x4000ff00));
    vcs::ge_gpu_backend_accumulate_color_triangles(
        alpha, rect(90, 160, 60, 60, 0xff00ff00));
    auto fog = d;
    fog.fog_enabled = true;
    fog.fog_color = 0xff0000;
    auto fv = rect(180, 160, 60, 60, 0xff0000ff);
    for (auto &v : fv)
      v.fog_factor = 0.5f;
    vcs::ge_gpu_backend_accumulate_color_triangles(fog, fv);
    auto blend = d;
    blend.blend_enabled = true;
    blend.blend_source_factor = 2;
    blend.blend_dest_factor = 3;
    vcs::ge_gpu_backend_accumulate_color_triangles(
        blend, rect(280, 160, 60, 60, 0x800000ff));
    check(vcs::ge_gpu_backend_finish_color_frame(1),
          vcs::ge_gpu_backend_report().message.c_str());
    pixel(0, 0, 0xff302010);
    pixel(30, 30, 0xff0000ff);
    pixel(60, 60, 0xff0000ff);
    pixel(130, 130, 0xff00ff00);
    pixel(150, 20, 0xff302010);
    pixel(170, 40, 0xff00ffff);
    pixel(270, 30, 0xff0000ff);
    pixel(340, 30, 0xff00ff00);
    pixel(270, 100, 0xffff0000);
    pixel(340, 100, 0xffffffff);
    pixel(30, 170, 0xff302010);
    pixel(100, 170, 0xff00ff00);
    pixel(200, 180, 0xff800080);
    pixel(300, 180, 0xbf181088, 2);
    auto p = vcs::ge_gpu_backend_game_frame_rgba();
    std::ofstream capture(dir / "vulkan-pixels.ppm", std::ios::binary);
    capture << "P6\n480 272\n255\n";
    for (std::size_t n = 0; n < p.size(); n += 4)
      capture.write(reinterpret_cast<const char *>(p.data() + n), 3);
    capture.close();
    // Replacing a texture after a frame must invalidate GPU storage, not retain
    // old texels.
    for (auto &c : colors)
      c = 0xffffff00;
    check(vcs::ge_gpu_backend_upload_decoded_texture(
              tex, 2, 2,
              {reinterpret_cast<const std::byte *>(colors), sizeof(colors)}),
          "Texture replacement");
    vcs::ge_gpu_backend_accumulate_color_triangles(
        tex, rect(260, 20, 100, 100, 0xffffffff));
    check(vcs::ge_gpu_backend_finish_color_frame(2), "Second frame");
    pixel(270, 30, 0xffffff00);

    // Render-to-texture feedback must use the GPU surface, including
    // same-target feedback.
    auto off = d;
    off.framebuffer_address = 0x04088000;
    vcs::ge_gpu_backend_accumulate_color_triangles(
        off, rect(0, 0, 480, 272, 0xffa04080));
    auto fb = d;
    fb.texture_enabled = true;
    fb.texture_address = off.framebuffer_address;
    fb.texture_width = 512;
    fb.texture_height = 512;
    fb.texture_function = 3;
    fb.texture_use_alpha = true;
    check(vcs::ge_gpu_backend_texture_available(fb),
          "GPU render target must be sampleable without CPU decode");
    auto quad = rect(360, 160, 80, 80, 0xffffffff);
    for (auto &v : quad) {
      v.u *= 240;
      v.v *= 136;
    }
    vcs::ge_gpu_backend_accumulate_color_triangles(fb, quad);
    check(vcs::ge_gpu_backend_finish_color_frame(3), "Feedback frame");
    pixel(400, 200, 0xffa04080);
    // Stencil replace and equality test must reject untouched pixels.
    auto st = d;
    st.stencil = {true, 1, 7, 255, 0, 0, 2};
    vcs::ge_gpu_backend_accumulate_color_triangles(
        st, rect(20, 230, 30, 30, 0xff00ff00));
    st.stencil.function = 2;
    st.stencil.zpass = 0;
    vcs::ge_gpu_backend_accumulate_color_triangles(
        st, rect(10, 220, 60, 50, 0xffffff00));
    // Real model-space vertices transformed by the GE's viewport and indexed
    // strip path.
    vcs::GeGpuHardwareTransform hw{};
    hw.model_to_clip = {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1};
    hw.viewport_scale_x = 240;
    hw.viewport_scale_y = 136;
    hw.viewport_scale_z = 32767.5f;
    hw.viewport_center_x = 240;
    hw.viewport_center_y = 136;
    hw.viewport_center_z = 32767.5f;
    hw.primitive = 4;
    std::array<vcs::GeGpuVertex, 4> model{};
    const float positions[4][2] = {
        {-.5f, .7f}, {-.3f, .7f}, {-.5f, .9f}, {-.3f, .9f}};
    for (unsigned n = 0; n < 4; ++n) {
      model[n].x = positions[n][0];
      model[n].y = positions[n][1];
      model[n].rgba = 0xff8040ff;
    }
    const std::array<unsigned, 4> indices = {0, 1, 2, 3};
    vcs::ge_gpu_backend_accumulate_hardware_triangles(d, hw, model, indices);
    check(vcs::ge_gpu_backend_finish_color_frame(4), "Stencil/transform frame");
    pixel(30, 240, 0xffffff00);
    pixel(15, 225, 0xff302010);
    pixel(140, 245, 0xff8040ff);
    if (hidden) {
      vcs::ge_gpu_backend_set_native_window(nullptr);
      DestroyWindow(hidden);
    }
    // Release all backend resources before process exit.
    vcs::shutdown_ge_gpu_backend();
    std::cout << "PASS: native Vulkan pixels, depth, scissor, textures, alpha "
                 "discard, fog, blending, texture replacement, framebuffer "
                 "feedback, stencil, indexed transforms; no window or "
                 "game assets used.\n";
    return 0;
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    vcs::shutdown_ge_gpu_backend();
    return 1;
  }
}
