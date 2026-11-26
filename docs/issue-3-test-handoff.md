# Issue #3: Windows performance test handoff

[Issue #3](https://github.com/GTTeancum/StarWars-RenegadeSquadron-PC/issues/3) describes jittery menu audio and slow motion in Instant Action. The supplied log shows an RTX 3050, Vulkan, 4× MSAA, and a 3440×1440 output window during the session. That output size is separate from the internal render target. The total frames and swapchain presentations in the log are counters, not an FPS or game-speed measurement.

1. On the same Windows system and Instant Action scene, compare stock Vulkan with the opt-in presentation experiment when an experimental executable is available. Keep the window size, internal resolution, MSAA, texture packs, and scene constant for that comparison. Try each run from a fresh launch.
2. Collect the log and note menu audio, game speed, and whether the experimental mode actually selected mailbox, immediate, or the default FIFO. Immediate mode may tear; a FIFO fallback is not a comparison of alternate modes. Normal launches should continue using the unchanged default.
3. As separate controls, change only output size, or compare the documented DirectX 12 backend. If using the optional HD pack, repeat without it rather than changing it alongside another variable.
4. The `[realtime-speed]` diagnostic can distinguish slow host throughput with regular guest vblanks from irregular guest timing. Neither by itself identifies the CPU, GPU, or another subsystem as the bottleneck.

Linux renderer tests are not a reproduction on the reporter’s hardware. Treat any experimental build as a test of a hypothesis, not confirmation that the issue is fixed.
