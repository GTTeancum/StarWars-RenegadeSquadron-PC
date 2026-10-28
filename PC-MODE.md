# PC mode

The default PC renderer is now **native Vulkan**. `-Renderer DirectX12` explicitly selects the older backend. Vulkan currently uses original GE vertex lighting, supports MSAA and direct presentation, and retains a readback for native captures. Enhanced per-pixel lighting, normal maps, sun shadows and bloom remain DirectX-only. See [Vulkan notes](docs/VULKAN.md).

The performance figures and enhanced-rendering implementation descriptions below describe the original DirectX 12 path, not a Vulkan benchmark.

`Play-RenegadeSquadronPC.cmd` now starts in **PC mode** by default. It runs the optimized build
(`work\build-perf\bin\RenegadeNative.exe`, built with `work\build-perf.cmd`) with the graphics card
drawing the game and presenting straight to the window. Rasterization runs on the GPU.

Measured on the Echo Base replay at 1280x720 (Ryzen 7 8745HS / Radeon 780M): about 58-59 frames per
second with all features on, against about 1.5 before this work.

## What PC mode changes

| Feature | What it does | Source |
|---|---|---|
| Graphics-card rendering | The game's draws go to DirectX 12 and straight to the window; no CPU drawing, no copy-back | existing recomp DX12 backend, now connected to the window |
| Graphics-card positioning | Vertex positioning on the GPU (verified against CPU positioning on 11 maps) | existing recomp path, now default |
| 60 fps game cap | Replaces Renegade's own 20 fps cap (Asura `s_fMaxFrameRate`) | Asura timer code |
| Per-pixel lighting | The game's own lights evaluated per pixel; highlights use the real camera direction | Asura PC `DynamicLights.fxh` |
| Sun shadows | Shadow map from the scene's dominant light; 12-tap soft filter; darkens the finished pixel | Asura PC `ApplyShadows.fx` |
| Bloom | Bright-pass, 4-tap blur passes, added before the HUD | Asura PC `FSFX_SM30_Bloom.fx` |
| Normal maps | `textures/<id>_n.png` (or `.dds`/`.tga`) next to replacement textures | Asura PC `NormalMap.fxh` |
| System messages | PSP message boxes drawn as a GPU overlay | new |
| Text entry and system messages | Profile names typed on the PC keyboard (Enter confirm, Esc cancel; controller A/B) in place of the PSP on-screen keyboard; drawn with the game's own menu fonts and colours (`host/game_font.cpp` reads GRAPHICS\FONTS.ASR) | Asura font chunks + PSP texture pages |
| In-game PC settings | Options > Video Options (window size, fullscreen, frame rate limit, lighting, shadows, bloom, fog), Controls > Gamepad Settings (look speed, deadzones, invert, layout), Quit Game on the main menu; also in the pause menu. Changes apply at once and are saved to `RenegadeSquadron.ini` | Asura console variables (`PC.*`, registered through the game's `AddVar`/`AddCmd`) bound by the game's own GUIMenu widgets; pages built by `work\tools\pcmods\build_pc_menus.py` into `mods\files` |
| Sprint toggle | `[Controller] SprintToggle` (default true), also the Sprint: Toggle/Hold row on the Controls page (front end and pause menu). Toggle: a press of sprint (left stick click / Left Shift) starts sprinting until pressed again or the player stops moving | `host/modern_input008.cpp` latches the sprint action the game reads (action 21) |
| Load screens | The load picture stays behind the progress bar for the whole load | the GPU backend no longer clears the displayed framebuffer implicitly each frame (PSP video memory persists; games clear with their own draws) |
| View centering | `[Controller] ViewCentering` (default false), also the View Centering checkbox on the Gamepad & Mouse page. Off: the infantry view stays where the player aimed instead of re-levelling after about 1.5 s without look input | Input only (no camera writes): while no pitch is given, the pitch axis reports a tiny value that alternates in sign each read, which nets to no movement but keeps the camera's idle timer from firing (`host/control_bridge008.cpp`); own design, the Asura reference has no equivalent |
| Keyboard prompts and menu keys | While the keyboard/mouse is the live device the prompt atlas and button textures are redrawn as key caps naming the bound keys in the game's menu font (`host/key_prompts.cpp`, own design: Asura PC uses its own PC atlas, which Renegade does not ship); d-pad prompts (including the hero offer's accept/decline) show the arrow keys as arrow caps; menus take the same `[Keyboard]` bindings as play (A Cross, B Circle, X Square, Y Triangle, LB/RB shoulders, Back Select, d-pad) plus arrows, Enter, Backspace; a wheel notch holds its binding for 6 vblanks so the game's polling sees it | prompt textures keyed by device in the override store and both renderer caches |
| Clickable prompts | A click on any menu prompt that shows a button icon (menu text `BU_CROSS`, `BU_SQUARE`...) presses that button, without moving the selection: spawn map Personalization/Customization/Select, Back/Select/Cancel/Clear hints | `host/menu_cursor.cpp` reads each text element's ID |
| Button prompts | Xbox glyphs in the game's button atlas (`pspbuttons`) and the single-button textures (`button_*`), installed into `mods\textures` by `work\tools\pcmods\build_button_atlas.py --install` from `buttonAtlas.png`; a pack file a modder has edited is left alone | texture replacement by name |
| Keyboard and mouse | WASD move, mouse look, mouse buttons fire/lock, Esc pauses; the game switches to whichever device was touched last; keys set in `RenegadeSquadron.ini` [Keyboard], mouse speed/invert in the Gamepad & Mouse page; mouse look smoothing `[Mouse] Smoothing` (seconds, default 0.1, 0 = raw); a click also starts on the PRESS START screen | Asura PC input (mouse velocity on the look axes through `Asura_ControlMapping_Axis` response/decay easing, keys mapped to controller actions), host side in `display_sdl.cpp` / `modern_input008.cpp` |
| Mouse in the menus | Pointer highlights the widget under it, left click selects, right click backs out, wheel steps up/down, sliders drag, list rows follow the pointer and accept on click (Instant Action planet/mode/era/playlist), the wheel over a list scrolls its rows with the highlight on the row under the pointer, the scroll bar beside a list drags or jumps on a click (the PSP thumb follows the selected entry, so these move the selection), numeric boxes step on a click of their left/right arrow; pages with nothing selectable (PRESS START) take a click as accept; Esc backs out of every page | Asura GUIMenu cursor path (`Menu_Page::ProcessInputActivity` with `m_bUseCursor`: `FindSelectableWidgetAtPos`, ROLL_IN/ROLL_OUT, CLICK as accept, slider `SetSliderFromCursorPos`), run by the host on the game's live menu objects because the PSP build was compiled without `ASURA_USE_CURSOR` (`host/menu_cursor.cpp`) |

## Launcher options

```
Play-RenegadeSquadronPC.ps1 -NoBloom
Play-RenegadeSquadronPC.ps1 -NoShadows
Play-RenegadeSquadronPC.ps1 -NoPerPixelLighting
Play-RenegadeSquadronPC.ps1 -SmoothFog
Play-RenegadeSquadronPC.ps1 -FrameRateCap 30
Play-RenegadeSquadronPC.ps1 -Renderer Software      # the original CPU renderer
```

Fine tuning through environment variables (set before launching):

| Variable | Default | Meaning |
|---|---|---|
| `RENEGADE_BLOOM_THRESHOLD` | 0.75 | Brightness above which pixels bloom |
| `RENEGADE_BLOOM_INTENSITY` | 1.0 | Strength of the added glow |
| `RENEGADE_BLOOM_ACCUMULATE` | 0 | 1 = Asura's trailing glow (washes out bright maps such as Hoth) |
| `RENEGADE_SHADOW_STRENGTH` | 0.75 | Shadow darkness (Asura `g_fShadowStrength` role) |
| `RENEGADE_SHADOW_RADIUS` | 30 | Half-width of the shadowed area around the camera, world units |
| `RENEGADE_SHADOW_SIZE` | 2048 | Shadow map resolution |
| `RENEGADE_SHADOW_BIAS` / `_SLOPE_BIAS` | 0.0006 / 0.003 | Self-shadowing bias |
| `RENEGADE_FOG_CURVE` | linear | `smooth` = smoothstep fade between the game's fog start and end |

Debug views: `RENEGADE_PER_PIXEL_LIGHTING=normals` (surface directions as colour),
`RENEGADE_SHADOWS=debug` (red = shadow, green = faces the sun, blue = inside the shadow area).

## Design decisions that are not straight from the Asura source

- **Bloom defaults.** Asura's component defaults (threshold 0.5, trailing glow on, warm orange tint)
  were overridden per level in AvP. Renegade has no such data; threshold 0.75, trailing glow off and a
  neutral tint hold across Echo Base, Hoth and Mustafar.
- **Sun direction.** Renegade lights each object with three single-colour directional lights sharing one
  direction (the PSP form of Asura's spherical-harmonic lighting). The sun is their brightness-weighted
  average over the frame's shadow casters; the world geometry itself carries no directional light.
- **Shadow casters.** Renegade's world geometry carries no lights: its lighting, including roofs blocking the
  sun and interior lamps, is baked into vertex colour, and characters are lit from light samples taken at
  their position. Real-time shadows therefore come only from characters, objects and vehicles (anything
  carrying lights); the static world relies on its baked shading, so interiors are not darkened twice.
- **Shared lighting space.** Renegade folds the camera into object matrices but draws terrain with a real
  view matrix; per-pixel lit draws are converted to camera space so terrain, objects, lights and the
  shadow map agree.
- **Normal maps on baked surfaces.** World surfaces have only baked lighting, which a normal map cannot
  affect. Where a normal map exists on such a surface, the baked colour is scaled by the map's change in
  response to the sun (exactly 1 where the map is flat). Asura PC lit these surfaces from per-vertex
  spherical-harmonic data that Renegade lacks.
- **Palette-animated textures.** Asura PC creates each texture once and never rewrites it. Renegade
  recolours some palettes every frame (space-battle ships), which re-decoded and re-uploaded those
  textures every frame (about 15 ms per frame in space). A palette texture whose colours keep changing is
  switched to a GPU palette: its indices are uploaded once and the palette is sent per draw and applied in
  the pixel shader. Space battles went from about 40 to about 58 fps at the 60 fps cap. Those textures cast
  shadows as solid shapes (the shadow pass does not apply the palette's transparency).
- **Fog curve.** Asura fades fog through a per-level curve texture; with no Renegade data the curve is
  an optional smoothstep. The default keeps the game's own linear fog.

## Known issues

- Shadows follow the camera's rotation; slight shimmer when turning is possible.
- Frame-to-frame timing varies slightly around 16.7 ms.
- The PC overlays (system message boxes and the keyboard text-entry box) use the game's menu fonts and
  colours; the layouts are host-drawn approximations of the front end's pages, not GUIMenu pages.
