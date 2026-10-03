#include "framebuffer_capture.hpp"
#include "ge_renderer.hpp"

#include "psprecomp/common.hpp"

#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>

namespace vcs {
namespace {

std::uint8_t expand_4(std::uint32_t value) noexcept {
    value &= 0xFu;
    return static_cast<std::uint8_t>((value << 4u) | value);
}

std::uint8_t expand_5(std::uint32_t value) noexcept {
    value &= 0x1Fu;
    return static_cast<std::uint8_t>((value << 3u) | (value >> 2u));
}

std::uint8_t expand_6(std::uint32_t value) noexcept {
    value &= 0x3Fu;
    return static_cast<std::uint8_t>((value << 2u) | (value >> 4u));
}

std::uint32_t bytes_per_pixel(std::uint32_t format) {
    if (format <= 2u) return 2u;
    if (format == 3u) return 4u;
    throw psprecomp::Error("Unsupported PSP framebuffer pixel format " + std::to_string(format));
}

std::uint64_t frame_hash(const std::vector<std::uint8_t> &rgb) noexcept {
    constexpr std::uint64_t offset = 1469598103934665603ull;
    constexpr std::uint64_t prime = 1099511628211ull;
    std::uint64_t hash = offset;
    for (const std::uint8_t byte : rgb) {
        hash ^= byte;
        hash *= prime;
    }
    return hash;
}

struct CaptureState {
    bool initialized{};
    bool enabled{};
    bool dump_duplicates{};
    std::filesystem::path directory;
    std::uint32_t limit{8u};
    std::uint64_t start_vblank{};
    std::uint64_t stride{1};
    std::uint64_t vblank_index{};
    std::uint32_t dumped{};
    std::optional<std::uint64_t> previous_hash;
};

CaptureState &capture_state() {
    static CaptureState state;
    return state;
}

void initialize_capture_state(CaptureState &state) {
    if (state.initialized) return;
    state.initialized = true;
    const char *directory = std::getenv("PSPRECOMP_FRAME_DUMP_DIR");
    if (directory == nullptr || *directory == '\0') return;
    state.directory = directory;
    state.enabled = true;
    state.dump_duplicates = std::getenv("PSPRECOMP_FRAME_DUMP_DUPLICATES") != nullptr;
    if(const char* text=std::getenv("PSPRECOMP_FRAME_DUMP_STRIDE")){char* end=nullptr;auto n=std::strtoull(text,&end,0);if(end!=text&&*end==0&&n>0)state.stride=n;}
    if (const char *limit = std::getenv("PSPRECOMP_FRAME_DUMP_LIMIT")) {
        char *end = nullptr;
        const unsigned long value = std::strtoul(limit, &end, 0);
        if (end != limit && *end == '\0' && value <= std::numeric_limits<std::uint32_t>::max())
            state.limit = static_cast<std::uint32_t>(value);
    }
    if (const char *start = std::getenv("PSPRECOMP_FRAME_DUMP_START")) {
        char *end = nullptr;
        const unsigned long long value = std::strtoull(start, &end, 0);
        if (end != start && *end == '\0') state.start_vblank = value;
    }
}

} // namespace

std::vector<std::uint8_t> decode_framebuffer_rgb(
    const psprecomp::GuestMemory &memory,
    const FramebufferDescription &description) {
    if (description.width == 0u || description.height == 0u)
        throw psprecomp::Error("PSP framebuffer dimensions must be non-zero");
    if (description.stride < description.width)
        throw psprecomp::Error("PSP framebuffer stride is smaller than its width");

    const std::uint32_t bpp = bytes_per_pixel(description.pixel_format);
    const std::uint64_t last_pixel =
        (static_cast<std::uint64_t>(description.height - 1u) * description.stride + description.width) * bpp;
    if (last_pixel > std::numeric_limits<std::size_t>::max() ||
        !memory.contains(description.address, static_cast<std::size_t>(last_pixel))) {
        throw psprecomp::Error("PSP framebuffer lies outside EDRAM/RAM at " +
                              psprecomp::hex32(description.address));
    }

    const std::uint64_t output_size =
        static_cast<std::uint64_t>(description.width) * description.height * 3u;
    if (output_size > std::numeric_limits<std::size_t>::max())
        throw psprecomp::Error("PSP framebuffer output size overflow");
    std::vector<std::uint8_t> rgb(static_cast<std::size_t>(output_size));

    std::size_t destination = 0u;
    for (std::uint32_t y = 0u; y < description.height; ++y) {
        std::uint32_t source = description.address + y * description.stride * bpp;
        for (std::uint32_t x = 0u; x < description.width; ++x, source += bpp) {
            std::uint8_t red{};
            std::uint8_t green{};
            std::uint8_t blue{};
            if (description.pixel_format == 3u) {
                const std::uint32_t pixel = memory.load32(source);
                red = static_cast<std::uint8_t>(pixel & 0xFFu);
                green = static_cast<std::uint8_t>((pixel >> 8u) & 0xFFu);
                blue = static_cast<std::uint8_t>((pixel >> 16u) & 0xFFu);
            } else {
                const std::uint16_t pixel = memory.load16(source);
                switch (description.pixel_format) {
                case 0u:
                    red = expand_5(pixel);
                    green = expand_6(pixel >> 5u);
                    blue = expand_5(pixel >> 11u);
                    break;
                case 1u:
                    red = expand_5(pixel);
                    green = expand_5(pixel >> 5u);
                    blue = expand_5(pixel >> 10u);
                    break;
                case 2u:
                    red = expand_4(pixel);
                    green = expand_4(pixel >> 4u);
                    blue = expand_4(pixel >> 8u);
                    break;
                default:
                    throw psprecomp::Error("Unsupported PSP framebuffer pixel format");
                }
            }
            rgb[destination++] = red;
            rgb[destination++] = green;
            rgb[destination++] = blue;
        }
    }
    return rgb;
}


std::vector<std::byte> decode_framebuffer_rgba(
    const psprecomp::GuestMemory &memory,
    const FramebufferDescription &description) {
    if (description.width == 0u || description.height == 0u)
        throw psprecomp::Error("PSP framebuffer dimensions must be non-zero");
    if (description.stride < description.width)
        throw psprecomp::Error("PSP framebuffer stride is smaller than its width");

    const std::uint32_t bpp = bytes_per_pixel(description.pixel_format);
    const std::uint64_t last_pixel =
        (static_cast<std::uint64_t>(description.height - 1u) * description.stride + description.width) * bpp;
    if (last_pixel > std::numeric_limits<std::size_t>::max() ||
        !memory.contains(description.address, static_cast<std::size_t>(last_pixel))) {
        throw psprecomp::Error("PSP framebuffer lies outside EDRAM/RAM at " +
                              psprecomp::hex32(description.address));
    }

    const std::uint64_t output_size =
        static_cast<std::uint64_t>(description.width) * description.height * 4u;
    if (output_size > std::numeric_limits<std::size_t>::max())
        throw psprecomp::Error("PSP framebuffer RGBA output size overflow");
    std::vector<std::byte> rgba(static_cast<std::size_t>(output_size));
    std::size_t destination = 0u;
    for (std::uint32_t y = 0u; y < description.height; ++y) {
        std::uint32_t source = description.address + y * description.stride * bpp;
        for (std::uint32_t x = 0u; x < description.width; ++x, source += bpp) {
            std::uint8_t red{}, green{}, blue{}, alpha{255u};
            if (description.pixel_format == 3u) {
                const std::uint32_t pixel = memory.load32(source);
                red = static_cast<std::uint8_t>(pixel & 0xFFu);
                green = static_cast<std::uint8_t>((pixel >> 8u) & 0xFFu);
                blue = static_cast<std::uint8_t>((pixel >> 16u) & 0xFFu);
                alpha = static_cast<std::uint8_t>((pixel >> 24u) & 0xFFu);
            } else {
                const std::uint16_t pixel = memory.load16(source);
                switch (description.pixel_format) {
                case 0u:
                    red = expand_5(pixel);
                    green = expand_6(pixel >> 5u);
                    blue = expand_5(pixel >> 11u);
                    break;
                case 1u:
                    red = expand_5(pixel);
                    green = expand_5(pixel >> 5u);
                    blue = expand_5(pixel >> 10u);
                    alpha = (pixel & 0x8000u) != 0u ? 255u : 0u;
                    break;
                case 2u:
                    red = expand_4(pixel);
                    green = expand_4(pixel >> 4u);
                    blue = expand_4(pixel >> 8u);
                    alpha = expand_4(pixel >> 12u);
                    break;
                default:
                    throw psprecomp::Error("Unsupported PSP framebuffer pixel format");
                }
            }
            rgba[destination++] = static_cast<std::byte>(red);
            rgba[destination++] = static_cast<std::byte>(green);
            rgba[destination++] = static_cast<std::byte>(blue);
            rgba[destination++] = static_cast<std::byte>(alpha);
        }
    }
    return rgba;
}

void write_framebuffer_ppm(const std::filesystem::path &path,
                           const FramebufferDescription &description,
                           const std::vector<std::uint8_t> &rgb) {
    const std::uint64_t expected =
        static_cast<std::uint64_t>(description.width) * description.height * 3u;
    if (rgb.size() != expected)
        throw psprecomp::Error("RGB framebuffer payload has an unexpected size");
    if (!path.parent_path().empty()) std::filesystem::create_directories(path.parent_path());
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    if (!output) throw psprecomp::Error("Could not create frame dump " + path.string());
    output << "P6\n" << description.width << ' ' << description.height << "\n255\n";
    output.write(reinterpret_cast<const char *>(rgb.data()), static_cast<std::streamsize>(rgb.size()));
    if (!output) throw psprecomp::Error("Could not finish frame dump " + path.string());
}

void capture_frame_if_requested(const psprecomp::GuestMemory &memory,
                                const FramebufferDescription &description) {
    CaptureState &state = capture_state();
    initialize_capture_state(state);
    ++state.vblank_index;
    ge_hd_frame_boundary(state.vblank_index);
    if (!state.enabled) return;
    if (state.vblank_index < state.start_vblank || (state.vblank_index-state.start_vblank)%state.stride!=0) return;
    if (state.limit != 0u && state.dumped >= state.limit) return;
    if (description.address == 0u || description.width == 0u || description.height == 0u ||
        description.stride == 0u) return;

    try {
        std::vector<std::uint8_t> rgb = decode_framebuffer_rgb(memory, description);
        const std::uint64_t hash = frame_hash(rgb);
        if (!state.dump_duplicates && state.previous_hash && *state.previous_hash == hash) return;
        state.previous_hash = hash;

        std::ostringstream filename;
        filename << "frame_" << std::setw(6) << std::setfill('0') << state.vblank_index << ".ppm";
        const std::filesystem::path path = state.directory / filename.str();
        write_framebuffer_ppm(path, description, rgb);
        if(auto hd=ge_hd_frame_rgb(description.address,description.pixel_format);!hd.empty()){
            auto hd_description=description;
            hd_description.width=1280;hd_description.height=720;hd_description.stride=1280;
            write_framebuffer_ppm(state.directory/"render-720p"/filename.str(),hd_description,hd);
            if(const char* fxaa=std::getenv("RENEGADE_FXAA");fxaa && std::string(fxaa)=="1"){
                write_framebuffer_ppm(state.directory/"render-720p-fxaa"/filename.str(),hd_description,
                                      ge_hd_frame_fxaa_rgb(description.address,description.pixel_format));
                if(const auto* report=std::getenv("RENEGADE_RENDER_REPORT");report&&*report)
                    write_framebuffer_ppm(state.directory/"render-720p-fxaa-whole-frame"/filename.str(),hd_description,ge_fxaa_rgb(hd,1280,720));
                std::cerr << "[frame] fxaa=1 output=1280x720 unfiltered_capture_preserved=1\n";
            }
            std::cerr << "[frame] shadow_raster=1280x720 native_guest_vram_preserved=1\n";
        }
        // Preserve the guest-native capture and emit a separate, explicitly
        // identified presentation image for reproducible headless comparisons.
        if (const char* output = std::getenv("RENEGADE_HEADLESS_OUTPUT_RESOLUTION")) {
            if (std::string(output) != "1280x720")
                throw psprecomp::Error("Headless output currently supports 1280x720 only");
            constexpr std::uint32_t ow=1280, oh=720;
            const double scale=std::min(double(ow)/description.width,double(oh)/description.height);
            const auto w=static_cast<std::uint32_t>(description.width*scale);
            const auto h=static_cast<std::uint32_t>(description.height*scale);
            std::vector<std::uint8_t> presentation(std::size_t(ow)*oh*3,0);
            for(std::uint32_t y=0;y<h;++y)for(std::uint32_t x=0;x<w;++x){
                const auto sx=std::uint64_t(x)*description.width/w;
                const auto sy=std::uint64_t(y)*description.height/h;
                const auto src=(sy*description.width+sx)*3;
                const auto dst=(std::size_t(y+(oh-h)/2)*ow+x+(ow-w)/2)*3;
                std::copy_n(rgb.data()+src,3,presentation.data()+dst);
            }
            auto output_description=description;
            output_description.width=ow;output_description.height=oh;output_description.stride=ow;
            write_framebuffer_ppm(state.directory/"presentation-720p"/filename.str(),output_description,presentation);
            std::cerr << "[frame] headless_output=1280x720 internal=" << description.width
                      << 'x' << description.height << " scaling=nearest aspect=preserved\n";
        }
        ++state.dumped;
        std::cerr << "[frame] dump=" << path.string()
                  << " address=" << psprecomp::hex32(description.address)
                  << " size=" << description.width << 'x' << description.height
                  << " stride=" << description.stride
                  << " format=" << description.pixel_format
                  << " hash=0x" << std::hex << hash << std::dec << "\n";
    } catch (const std::exception &error) {
        std::cerr << "[frame] capture failed: " << error.what() << "\n";
    }
}

void reset_frame_capture() noexcept {
    capture_state() = CaptureState{};
}

} // namespace vcs
