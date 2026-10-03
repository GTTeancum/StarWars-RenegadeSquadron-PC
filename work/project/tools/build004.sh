#!/usr/bin/env bash
# Build the Linux host using an explicitly verified generated-code archive.
# Full regeneration remains available by omitting RENEGADE_PREBUILT_AOT in CMake.
set -euo pipefail
R="${RENEGADE_ROOT:-/mnt/data/renegade}"
AOT="${RENEGADE_AOT_ARCHIVE:-$R/prebuilt/linux-x86_64/librenegade_aot.a}"
if [[ ! -f "$AOT" && -f "$R/checkpoint003C/prebuilt/linux-x86_64/librenegade_aot.a" ]]; then
    AOT="$R/checkpoint003C/prebuilt/linux-x86_64/librenegade_aot.a"
fi
[[ -f "$AOT" ]] || { echo "Verified saved AOT archive is required: $AOT" >&2; exit 2; }
cmake -S "$R/intake/sources/PSPRecomp" -B "$R/intake/out/native004" -G Ninja \
 -DCMAKE_BUILD_TYPE=Release -DPSPRECOMP_PROFILE=renegade \
 -DRENEGADE_DISC_ROOT="$R/game/disc" -DRENEGADE_PREBUILT_AOT="$AOT" \
 -DRENEGADE_AOT_BINDING="$R/tools/aot-binding004.json" \
 -DRENEGADE_AOT_VERIFIER="$R/tools/verify_aot004.py"
cmake --build "$R/intake/out/native004" --parallel "${JOBS:-2}"
ctest --test-dir "$R/intake/out/native004" --output-on-failure
