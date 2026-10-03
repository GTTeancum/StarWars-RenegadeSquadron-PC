#!/bin/bash
set -euo pipefail
R=/mnt/data/renegade
B="$R/intake/out/framework"
SRC="$R/intake/sources/PSPRecomp"
"$B/psp_analyze" "$R/game/disc/PSP_GAME/SYSDIR/BOOT.BIN" "$R/analysis/boot.json"
"$B/psp_recomp" "$R/game/disc/PSP_GAME/SYSDIR/BOOT.BIN" --auto "$SRC/profiles/renegade/generated" 0x08804000 8192
