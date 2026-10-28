#!/usr/bin/env bash
# Requires CMake, Ninja, C++20 compiler, Python, SDL2 and FFmpeg development files,
# Vulkan headers, and a Linux DXC shader compiler. No system installation occurs.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
mkdir -p .local/linux-tmp .local/linux-cache
export TMPDIR="$root/.local/linux-tmp" XDG_CACHE_HOME="$root/.local/linux-cache"
options=()
if [[ -d .local/linux-deps/sdk ]]; then
  sdk="$root/.local/linux-deps/sdk"
  options+=("-DRENEGADE_SDK=$sdk" "-DCMAKE_LIBRARY_PATH=$sdk/usr/lib/x86_64-linux-gnu/sdl2-compat;$sdk/usr/lib/x86_64-linux-gnu")
  export LD_LIBRARY_PATH="$sdk/usr/lib/x86_64-linux-gnu/sdl2-compat:$sdk/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
if [[ -x .local/linux-deps/dxc/bin/dxc ]]; then
  options+=("-DRENEGADE_DXC=$root/.local/linux-deps/dxc/bin/dxc")
fi
cmake -S work/project/source -B .local/build-linux -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER="${CXX:-clang++}" \
  -DPSPRECOMP_PROFILE=renegade -DPSPRECOMP_BUILD_TESTS=OFF \
  -DPSPRECOMP_BUILD_VULKAN_TESTS=ON "${options[@]}" "$@"
cmake --build .local/build-linux --target RenegadeSquadron renegade_vulkan_tests --parallel "${JOBS:-4}"
