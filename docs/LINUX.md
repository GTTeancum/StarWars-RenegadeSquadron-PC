# Linux / local WSL build

The Linux player uses native Vulkan with SDL2 window surfaces. DirectX 12 remains Windows-only. The same generated game code and user-owned ULUS10292 disc data are used on both platforms.

Build requirements: a C++20 compiler (tested with Clang 21), CMake, Ninja, Python 3.10+, SDL2 development files, FFmpeg development files, Vulkan headers, and a Linux DXC shader compiler. Generated sources must already exist under `work/project/source/profiles/renegade/generated`.

From the repository root:

```sh
JOBS=4 bash work/build-linux.sh
bash work/run-linux.sh
```

The executable is `.local/build-linux/bin/RenegadeSquadron` (an ELF Linux binary, without `.exe`). The runner uses `data/PSP_GAME`, the Vulkan preset, and repository-local temporary/cache directories. It sets the stack to 16 MiB and loads a repository-local SDK if present. Saves stay with the executable. To use the installed layout and automatic ISO extraction directly, place an ISO or `data/PSP_GAME` beside the executable and run it without arguments; put the INI there as well.

For the local WSL build, SDL2 headers, SDL2-compat, SDL3, and libXss were downloaded as Ubuntu packages and extracted under `.local/linux-deps/sdk`; no system packages were installed. Linux DXC v1.9.2609 is under `.local/linux-deps/dxc`. Dependency hashes are recorded in `.local/linux-deps/SHA256SUMS`. Vulkan headers are reused from `.local/Vulkan-Headers`. FFmpeg development libraries and the Vulkan runtime were already installed in Ubuntu.

## Smoke test

```sh
bash work/smoke-linux.sh
```

This runs recorded controller input entirely within the game process, with a ten-minute watchdog and no desktop input. It captures difficulty selection, Hoth team selection, gameplay, and audio under `.local/runs/linux-hoth`. A successful exit alone does not prove visuals: inspect the captures.

The local WSL installation exposes Mesa llvmpipe as its Vulkan device. This is CPU software Vulkan, so these results do not establish native Linux GPU performance or Radeon hardware acceleration through WSL. Linux graphical interaction, speaker playback, and physical controls need separate testing. The Vulkan enhanced-lighting limitations described in the 0.9.1 notes still apply.

On 2026-10-28, the Ubuntu 26.04 WSL build passed all three Vulkan pixel/presentation tests and completed the Hoth replay through vblank 2600 at 1280x720 with 4x MSAA, exit 0. The difficulty, team-selection, and gameplay captures were individually inspected: menu text/backgrounds, player, AT-AT, snow terrain, sky, and HUD were present and textured. Audio capture contained 45.4 seconds of non-silent stereo PCM. Existing network/module and `sceIoDevctl` diagnostics also occur in the Windows run; they did not stop this match. The Windows Vulkan test suite also passed after the shared portability changes.
