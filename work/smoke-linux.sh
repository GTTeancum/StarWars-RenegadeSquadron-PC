#!/usr/bin/env bash
# Normal controller replay inside the game process; no desktop input.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
run="$root/.local/runs/linux-hoth"
mkdir -p "$run" .local/linux-tmp .local/linux-cache
export TMPDIR="$root/.local/linux-tmp" XDG_CACHE_HOME="$root/.local/linux-cache"
sdk="$root/.local/linux-deps/sdk"
if [[ -d "$sdk" ]]; then
  export LD_LIBRARY_PATH="$sdk/usr/lib/x86_64-linux-gnu/sdl2-compat:$sdk/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
cp .local/build-linux/bin/RenegadeSquadron "$run/RenegadeSquadron"
export PSPRECOMP_CONFIG="$root/work/rendering/vulkan.ini" PSPRECOMP_GE_BACKEND=vulkan
export PSPRECOMP_WINDOW=0 PSPRECOMP_AUDIO=1 SDL_AUDIODRIVER=dummy
export PSPRECOMP_AUDIO_WAV="$run/audio.wav" PSPRECOMP_FRAME_LIMIT=0 PSPRECOMP_RASTER_THREADS=1
export PSPRECOMP_STOP_VBLANK=2600 PSPRECOMP_GE_GPU_SKIP_SOFTWARE_RASTER=1 PSPRECOMP_DX12_GE_READBACK=1
export PSPRECOMP_GE_GPU_HW_TRANSFORM=1 PSPRECOMP_GE_GPU_HW_CULL=0
export PSPRECOMP_GE_GPU_DUMP_VBLANK=1400 PSPRECOMP_GE_GPU_DUMP_STRIDE=600
export PSPRECOMP_GE_GPU_DUMP_PATH="$run/frame.ppm"
export RENEGADE_FRAME_RATE_CAP=60 RENEGADE_CONTROLS=modern
export RENEGADE_PER_PIXEL_LIGHTING=0 RENEGADE_SHADOWS=0 RENEGADE_BLOOM=0
export RENEGADE_INPUT_REPLAY="$root/work/textures107-hoth-gcw-gpu-replay.txt"
ulimit -s 16384
cd "$run"
timeout --signal=TERM --kill-after=5s 600s ./RenegadeSquadron "$root/data/PSP_GAME/SYSDIR/BOOT.BIN" "$root/data" 1000000000000 >stdout.log 2>stderr.log
echo 'Linux Hoth smoke exited successfully; inspect the native captures before accepting visuals.'
