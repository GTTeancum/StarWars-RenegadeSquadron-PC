# Modern controls launcher

Run the game from the repository root with:

```powershell
.\Play-RenegadeSquadronPC.cmd
```

The launcher starts `work\build-windows-native\bin\RenegadeNative.exe` with the verified `BOOT.BIN` and extracted disc root already filled in. It also enables SDL's Xbox/XInput-friendly controller path before the game starts and selects the opt-in modern Renegade controls profile.

Default modern mapping:

| Input | Action |
|---|---|
| Left stick | Move forward/back and strafe |
| Right stick | Look yaw/pitch |
| Right trigger | Fire / primary shooter action |
| Left trigger | Lock/focus action |
| A | Jump |
| Left stick click | Sprint |
| Right shoulder | Secondary mapped action |
| X | Interaction/equipment action |
| D-pad up/down | Jetpack rise/descend where that context is active |

Useful options:

```powershell
.\Play-RenegadeSquadronPC.ps1 -Resolution 1280x720
.\Play-RenegadeSquadronPC.ps1 -LookX 1.25 -LookY 1.15
.\Play-RenegadeSquadronPC.ps1 -InvertY
.\Play-RenegadeSquadronPC.ps1 -DryRun
```

The default deadzones are the verified XInput-style values already used by the native modern controls tests: left stick `0.2394`, right stick `0.2652`, trigger threshold `0.1176`.
