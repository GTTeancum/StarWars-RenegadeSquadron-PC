#include "override_texture.hpp"
#include <algorithm>
#include <cctype>
#include <fstream>
#include <stdexcept>
#include <memory>
extern "C" {
#include <libavcodec/avcodec.h>
#include <libswscale/swscale.h>
}

namespace renegade::overrides {
namespace {
struct Decoder {
    AVCodecContext* context{};
    AVPacket* packet{};
    AVFrame* frame{};
    SwsContext* scaler{};
    ~Decoder() {
        sws_freeContext(scaler);
        av_frame_free(&frame);
        av_packet_free(&packet);
        avcodec_free_context(&context);
    }
};
void require(bool valid, const char* message) {
    if (!valid) throw std::runtime_error(message);
}
}
bool load_texture(const std::filesystem::path& path, Texture& output, std::string& error) {
    try {
        auto extension = path.extension().string();
        std::transform(extension.begin(), extension.end(), extension.begin(),
            [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
        AVCodecID id = extension == ".png" ? AV_CODEC_ID_PNG :
                       extension == ".tga" ? AV_CODEC_ID_TARGA :
                       extension == ".dds" ? AV_CODEC_ID_DDS : AV_CODEC_ID_NONE;
        require(id != AV_CODEC_ID_NONE, "Expected .dds, .tga or .png");
        std::ifstream file(path, std::ios::binary | std::ios::ate);
        require(bool(file), "Cannot open override texture");
        auto size = file.tellg();
        require(size > 0 && size <= 128 * 1024 * 1024, "Texture file exceeds size limit or is empty");
        const AVCodec* codec = avcodec_find_decoder(id);
        require(codec != nullptr, "Required image decoder unavailable in FFmpeg");
        Decoder decoder;
        decoder.context = avcodec_alloc_context3(codec);
        decoder.packet = av_packet_alloc();
        decoder.frame = av_frame_alloc();
        require(decoder.context && decoder.packet && decoder.frame, "Image decoder allocation failed");
        decoder.context->max_pixels = 4096ll * 4096ll;
        decoder.context->thread_count = 1;
        decoder.context->err_recognition = AV_EF_CRCCHECK | AV_EF_BITSTREAM | AV_EF_EXPLODE;
        require(avcodec_open2(decoder.context, codec, nullptr) >= 0, "Cannot initialize image decoder");
        require(av_new_packet(decoder.packet, static_cast<int>(size)) >= 0, "Image packet allocation failed");
        file.seekg(0);
        require(bool(file.read(reinterpret_cast<char*>(decoder.packet->data), size)), "Texture read failed");
        require(avcodec_send_packet(decoder.context, decoder.packet) >= 0, "Invalid texture data");
        require(avcodec_receive_frame(decoder.context, decoder.frame) >= 0, "Texture decoding failed");
        auto* frame = decoder.frame;
        require(frame->width > 0 && frame->height > 0 && frame->width <= 4096 && frame->height <= 4096,
                "Texture dimensions must be between 1 and 4096");
        Texture result;
        result.width = frame->width;
        result.height = frame->height;
        result.rgba.resize(static_cast<std::size_t>(result.width) * result.height * 4);
        decoder.scaler = sws_getContext(frame->width, frame->height,
            static_cast<AVPixelFormat>(frame->format), frame->width, frame->height,
            AV_PIX_FMT_RGBA, SWS_POINT, nullptr, nullptr, nullptr);
        require(decoder.scaler != nullptr, "Unsupported decoded image format");
        std::uint8_t* dest[] = { result.rgba.data(), nullptr, nullptr, nullptr };
        int stride[] = { frame->width * 4, 0, 0, 0 };
        require(sws_scale(decoder.scaler, frame->data, frame->linesize, 0, frame->height, dest, stride)
                == frame->height, "Image conversion failed");
        output = std::move(result);
        error.clear();
        return true;
    } catch (const std::exception& ex) {
        error = ex.what();
        return false;
    }
}
}
