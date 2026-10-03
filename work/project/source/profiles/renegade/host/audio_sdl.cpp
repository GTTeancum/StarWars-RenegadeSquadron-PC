#include "audio_output.hpp"
#include "audio_resampler.hpp"
#include "vcs_config.hpp"
#include "psprecomp/common.hpp"
#include <SDL2/SDL.h>
#include <array>
#include <vector>
#include <fstream>
#include <mutex>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <algorithm>
namespace vcs { namespace {
constexpr std::uint64_t rate=44100,ringframes=rate*4,block=512,margin=1024;
struct Channel{StreamingLinearResampler resampler;std::uint64_t cursor{};std::uint32_t frequency{44100};bool active{},stereo{true};};
struct State{std::mutex mutex;SDL_AudioDeviceID device{};bool initialized{},anchored{};std::uint64_t anchor{},output{},late{},overrun{},resync{},device_dropped{},wavframes{};std::vector<std::int64_t> ring;std::array<Channel,9> channels;std::ofstream wav;};
State state;
void u16(std::ostream& f,std::uint16_t n){for(unsigned i=0;i<2;++i)f.put(static_cast<char>(n>>(8*i)));}
void u32(std::ostream& f,std::uint32_t n){for(unsigned i=0;i<4;++i)f.put(static_cast<char>(n>>(8*i)));}
void wavheader(std::ostream& f,std::uint64_t frames){if(frames>(0xffffffffull-44)/4)throw psprecomp::Error("WAV capture exceeded RIFF limit");auto size=static_cast<std::uint32_t>(frames*4);f.write("RIFF",4);u32(f,size+36);f.write("WAVEfmt ",8);u32(f,16);u16(f,1);u16(f,2);u32(f,44100);u32(f,44100*4);u16(f,4);u16(f,16);f.write("data",4);u32(f,size);}
void initialize(){if(state.initialized)return;state.ring.resize(ringframes*2);state.initialized=true;
 if(SDL_InitSubSystem(SDL_INIT_AUDIO)!=0)throw psprecomp::Error(std::string("SDL audio init: ")+SDL_GetError());SDL_AudioSpec desired{},actual{};desired.freq=44100;desired.format=AUDIO_S16SYS;desired.channels=2;desired.samples=512;
 state.device=SDL_OpenAudioDevice(nullptr,0,&desired,&actual,0);if(!state.device)throw psprecomp::Error(std::string("SDL audio device: ")+SDL_GetError());SDL_PauseAudioDevice(state.device,0);
 if(auto path=std::getenv("PSPRECOMP_AUDIO_WAV")){state.wav.open(path,std::ios::binary|std::ios::trunc);if(!state.wav)throw psprecomp::Error("Cannot create requested WAV capture");wavheader(state.wav,0);}
 std::cerr<<"[audio-sdl] 44100 Hz stereo PCM, virtual-time mix and persistent resamplers\n";
}
std::uint64_t frame(std::uint64_t time){return time>state.anchor?(time-state.anchor)*rate/1000000:0;}
void queue(std::uint64_t count){std::vector<std::int16_t> samples(count*2);for(std::uint64_t i=0;i<count;++i)for(unsigned ch=0;ch<2;++ch){auto slot=((state.output+i)%ringframes)*2+ch;samples[i*2+ch]=static_cast<std::int16_t>(std::clamp<std::int64_t>(state.ring[slot],-32768,32767));state.ring[slot]=0;}
 if(state.wav.is_open()){state.wav.write(reinterpret_cast<const char*>(samples.data()),static_cast<std::streamsize>(samples.size()*2));if(!state.wav)throw psprecomp::Error("WAV capture write failed");state.wavframes+=count;}
 // Wall-clock output may lag during offline accelerated execution. Preserve the
 // complete virtual-time WAV, while bounding the interactive device queue.
 if(state.device){if(SDL_GetQueuedAudioSize(state.device)>44100*4*2){SDL_ClearQueuedAudio(state.device);++state.device_dropped;}if(SDL_QueueAudio(state.device,samples.data(),static_cast<Uint32>(samples.size()*2))!=0)throw psprecomp::Error(SDL_GetError());}
 state.output+=count;
}
void advance(std::uint64_t time){if(!state.anchored)return;auto now=frame(time),end=now>margin?now-margin:0;while(end>=state.output+block)queue(block);}
}
bool audio_output_enabled(){const char* v=std::getenv("PSPRECOMP_AUDIO");return (v&&*v&&std::strcmp(v,"0")!=0)||std::getenv("PSPRECOMP_AUDIO_WAV");}
void audio_output_submit(std::span<const std::int16_t> pcm,std::uint32_t frames,bool stereo,std::uint32_t left,std::uint32_t right,std::uint32_t source_rate,std::uint32_t channel,std::uint64_t guest_time_us){
 if(!audio_output_enabled()||!frames)return;if(channel>=9||!source_rate||pcm.size()<std::size_t(frames)*(stereo?2:1))throw psprecomp::Error("Invalid host audio submission");std::lock_guard guard(state.mutex);initialize();
 if(!state.anchored){state.anchor=guest_time_us;state.anchored=true;}
 advance(guest_time_us);auto& ch=state.channels[channel];auto scheduled=frame(guest_time_us);auto distance=ch.cursor>scheduled?ch.cursor-scheduled:scheduled-ch.cursor;
 if(!ch.active || ch.frequency!=source_rate || ch.stereo!=stereo || distance>64){if(ch.active)++state.resync;ch=Channel{};ch.active=true;ch.frequency=source_rate;ch.stereo=stereo;ch.cursor=std::max(scheduled,state.output);ch.resampler.reset(source_rate,stereo);}
 if(ch.cursor<state.output){state.late+=state.output-ch.cursor;ch.cursor=state.output;ch.resampler.reset(source_rate,stereo);}
 auto master=std::min<unsigned>(vcs_configuration().audio.volume,100);auto lg=std::int64_t(std::min(left,0x8000u))*master/100,rg=std::int64_t(std::min(right,0x8000u))*master/100;
 ch.resampler.process(pcm,frames,stereo,source_rate,[&](std::int16_t l,std::int16_t r){if(ch.cursor>=state.output+ringframes-block){++state.overrun;++ch.cursor;return;}auto slot=(ch.cursor%ringframes)*2;state.ring[slot]+=(std::int64_t(l)*lg)>>15;state.ring[slot+1]+=(std::int64_t(r)*rg)>>15;++ch.cursor;});advance(guest_time_us);
}
void audio_output_advance(std::uint64_t time){if(!audio_output_enabled())return;std::lock_guard guard(state.mutex);if(state.initialized)advance(time);}
void audio_output_reset_channel(std::uint32_t ch){std::lock_guard guard(state.mutex);if(ch<9)state.channels[ch]=Channel{};}
void audio_output_shutdown(){std::lock_guard guard(state.mutex);if(!state.initialized)return;std::uint64_t end=state.output;for(auto& c:state.channels)end=std::max(end,c.cursor);end=std::min(end,state.output+ringframes);while(end>state.output)queue(std::min(block,end-state.output));
 if(state.wav.is_open()){state.wav.seekp(0);wavheader(state.wav,state.wavframes);state.wav.close();}
 std::cerr<<"[audio-sdl] frames="<<state.wavframes<<" late="<<state.late<<" overrun="<<state.overrun<<" resync="<<state.resync<<" device_queue_resets="<<state.device_dropped<<"\n";
 if(state.device)SDL_CloseAudioDevice(state.device);state.device=0;SDL_QuitSubSystem(SDL_INIT_AUDIO);state.initialized=state.anchored=false;state.ring.clear();state.channels={};state.output=state.anchor=state.late=state.overrun=state.resync=state.device_dropped=state.wavframes=0;
}
}
