#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
mkdir -p .local/linux-tmp .local/linux-cache
export TMPDIR="$root/.local/linux-tmp" XDG_CACHE_HOME="$root/.local/linux-cache"
sdk="$root/.local/linux-deps/sdk"
if [[ -d "$sdk" ]]; then
  export LD_LIBRARY_PATH="$sdk/usr/lib/x86_64-linux-gnu/sdl2-compat:$sdk/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
ulimit -s 16384
exe="$root/.local/build-linux/bin/RenegadeSquadron"
if [[ $# -gt 0 ]]; then
  exec "$exe" "$@"
fi
export PSPRECOMP_CONFIG="${PSPRECOMP_CONFIG:-$root/work/rendering/vulkan.ini}"
exec "$exe" "$root/data/PSP_GAME/SYSDIR/BOOT.BIN" "$root/data" 1000000000000
