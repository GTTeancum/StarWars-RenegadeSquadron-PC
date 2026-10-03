#!/bin/bash
set -u
ROOT=/mnt/data/renegade
R="$ROOT/intake/sources/PSPRecomp"
B="$ROOT/intake/out/framework"
GAME="$ROOT/game/disc/PSP_GAME/SYSDIR/BOOT.BIN"
finish() { echo "$1" > "$ROOT/logs/build-native.exit"; exit "$1"; }
"$B/psp_analyze" "$GAME" "$ROOT/analysis/boot.json" > "$ROOT/logs/analyze.log" 2>&1 || finish $?
/usr/bin/time -v "$B/psp_recomp" "$GAME" --auto "$R/profiles/renegade/generated" 0x08804000 8192 > "$ROOT/logs/codegen.log" 2>&1 || finish $?
cmake -S "$R" -B "$ROOT/intake/out/renegade" -G Ninja -DPSPRECOMP_PROFILE=renegade -DCMAKE_BUILD_TYPE=Release || finish $?
cmake --build "$ROOT/intake/out/renegade" --target RenegadeNative --parallel 4
finish $?
