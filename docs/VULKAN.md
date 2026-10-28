# Native Vulkan renderer

Vulkan is the installed player's and PC launcher's default. This backend calls Vulkan directly through the graphics driver's `vulkan-1.dll`; it does not wrap DirectX with a translation layer. `Backend=DirectX12` and `Backend=Software` remain available in the configuration. Explicit `PSPRECOMP_GE_BACKEND` overrides the INI selection.

The backend consumes the existing GE frontend's decoded geometry and textures. It supports textured triangle lists and indexed strips/fans, original vertex lighting, depth, stencil, scissor, alpha tests, common PSP blend modes, texture functions, mip chains, fog, persistent render targets, GPU framebuffer feedback, MSAA resolve, CPU readback for native captures, and a Win32 Vulkan swapchain. Hardware-transform submissions use the game's matrices; the initial backend computes the viewport transform on the CPU. Unsupported doubled-alpha/absolute-difference blend modes report a rendering error rather than silently using an incorrect mode.

The initial implementation submits synchronously and reads each completed frame back for diagnostics. It needs further performance work. Enhanced per-pixel lighting, normal maps, shadows and bloom remain DirectX-only; Vulkan uses the original GE vertex lighting. Do not interpret the pre-existing DirectX benchmark as a Vulkan benchmark.

## Build

Run `work/restore-vulkan-dependencies.ps1` to download pinned, SHA-256-verified Vulkan headers and DXC inside `.local`. The script does not install anything globally. An installed SDK may also satisfy CMake's discovery. DXC compiles the checked-in HLSL to embedded SPIR-V during the build; players do not need DXC or an SDK.

`work/test-vulkan.cmd` builds and runs asset-free pixel tests with both 1x and 4x MSAA requested. Tests verify actual readback pixels for overlapping depth-tested draws, scissor, texture orientation/update, alpha discard, blending, fog, framebuffer feedback, stencil, and indexed transforms. The image is saved inside `.local/build-vulkan`. A third test presents through a native Vulkan swapchain attached to an invisible window owned by the test process. No window is shown or activated, and no desktop input is generated.

The game still requires translated C++ generated from the user's supported BOOT.BIN. Generate and build as described in the main README. `RenegadeSquadron` is the no-console player target; `RenegadeNative` is the console diagnostic target.

## First-run disc preparation

Place a single US Renegade Squadron ISO beside the player executable. When `data/PSP_GAME` is absent, the player reads ISO9660 files into a staging directory under `data`, verifies BOOT.BIN and PARAM.SFO identities, then renames the completed PSP_GAME directory into place. The ISO is opened read-only. Existing complete game data is reused. Missing/ambiguous ISOs, malformed paths, links/junctions, unsupported disc layouts, wrong game versions and partial existing installations produce actionable errors. An interrupted extraction does not publish a partial PSP_GAME directory.

`RenegadeNative --prepare-data` performs setup and identity checks without running the game. The extractor test executable also exercises extraction and repeat-launch preservation. On the supplied disc, all 276 extracted files were verified against an independent 7-Zip extraction.

Interactive presentation, controllers and audible audio require testing the player. Offscreen pixel tests alone are not proof that the complete game works.

## Local verification

The final Windows build was checked on an AMD Radeon 780M with Vulkan at 1280x720 and 4x MSAA. Bounded headless game runs rendered the startup movies, title screen, profile/difficulty selection and Instant Action setup. Native frame captures were inspected. At recorded vblank 1400, the Vulkan and DirectX 12 difficulty-menu RGB captures were identical pixel-for-pixel. A texture-cache regression was fixed and tested: an omitted per-frame checksum now reuses a previously validated image instead of uploading it again.

The packaged no-console player also passed a bounded no-argument launch and selected Vulkan by default. Full gameplay, visible-window behavior, audible audio and physical controller use remain for interactive testing. The automated audio sink was a dummy device, so audio sample production is not an audible-audio acceptance claim.
