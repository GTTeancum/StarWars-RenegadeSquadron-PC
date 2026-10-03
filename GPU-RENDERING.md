# GPU rendering preview

Checkpoint 094 verifies the Echo Base preview at 720p: world geometry and characters render, and the minimap is correctly masked. Checkpoints 092/093 preserve the rejected images that exposed missing depth-clear and stencil behavior. Software remains the default while broader map coverage is pending.

Launch `Play-GPU-Preview.cmd` from the repository root. For your manual replacements, launch `Play-User-Textures.cmd -Renderer DirectX12`. Software remains the default in the normal launcher.

The DirectX 12 path renders at 1280x720, requests up to 4x MSAA, uses 24-bit depth with 8-bit stencil, presents through SDL with HUD-preserving FXAA, and retains modern/XInput controls and original texture dumping. It uploads replacement DDS/TGA/PNG images at their decoded dimensions, with no rotation, channel swap, newly generated mipmaps or anisotropic filtering. Replacement uploads contain one full-size image level. Original-alpha sidecars remain supported. F9 and `-InspectTextures` show/save the reference raster's scene/UI texture information.

This preview supports **texture-only packs**. A pack with a `models` directory is rejected so it cannot silently lose MSH/model overrides. Keep using Software for converted mesh, actor skin, gloss and normal-map materials. GPU integration of those features remains unfinished.

The CPU reference raster remains active for guest VRAM correctness and HUD coverage. GPU frames are read back for SDL presentation; this avoids replacing the existing controls/toolbar but has a transfer cost. Real-time performance is not guaranteed. MSAA availability depends on the adapter; startup logs record the selected count. DirectX initialization fails explicitly rather than silently falling back.

Reproduce the final Echo Base capture with `Capture-Rendering-Diagnostics.ps1 -Renderer DirectX12 -Name my-gpu-run`. Use Software for the reference capture, or `-OriginalBaseline` for original assets. Preserve each unique run name. Captures run headlessly with no window. Both retain original dumps; GPU capture includes `gpu.ppm` and `gpu-fxaa.ppm` at the actual internal dimensions. Run `work/test-rendering.cmd` to rebuild and run the renderer regression checks.

This verifies one route, not every map, space mode, effect or PSP rendering state. GPU stencil tests exercise 8888 alpha storage; 5551/4444 quantization and sampled framebuffer-alpha/stencil synchronization remain unverified. Guest CPU framebuffer writes and unsupported primitives still need parity coverage. Rendering preserves the supplied image content and resolution; it does not create detail missing from that image.

Checkpoint104 adds current-boundary1280x720 GPU/FXAA controller captures and a guided Yavin tutorial through the recon-droid objective. Checkpoint105 fixes the reproduced black campaign movies with a decoded-picture upload, preserving aspect, orientation and color channels. Both tested movie scenes match their same-boundary software references; normal spawn/gameplay returns afterward. All11 rendering tests pass. This targeted movie repair does not establish general CPU framebuffer/feedback parity. Mipmap/filtering changes remain skipped. See `outputs/RENDERING-104.md` and `outputs/RENDERING-105.md` for grouped evidence and the corresponding verification JSONs for hashes and limits.
