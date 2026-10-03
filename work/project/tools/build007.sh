#!/usr/bin/env bash
set -euo pipefail
R="${RENEGADE_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
BUILD="${RENEGADE_BUILD_DIRECTORY:-$R/intake/out/native007}"
AOT="${RENEGADE_AOT_ARCHIVE:-$R/prebuilt/linux-x86_64/librenegade_aot.a}"
[[ -f "$R/intake/sources/PSPRecomp/CMakeLists.txt" ]] || { echo "Restore source under intake/sources/PSPRecomp first" >&2; exit 2; }
[[ -d "$R/intake/sdk/usr/include" ]] || { echo "Bootstrap the supplied offline intake SDK first" >&2; exit 2; }
cmake -S "$R/intake/sources/PSPRecomp" -B "$BUILD" -G Ninja \
 -DCMAKE_BUILD_TYPE=Release -DPSPRECOMP_PROFILE=renegade \
 -DRENEGADE_SDK="$R/intake/sdk" -DRENEGADE_DISC_ROOT="$R/game/disc" \
 -DRENEGADE_PREBUILT_AOT="$AOT" -DRENEGADE_AOT_BINDING="$R/tools/aot-binding004.json" \
 -DRENEGADE_AOT_VERIFIER="$R/tools/verify_aot004.py"
cmake --build "$BUILD" --parallel "${JOBS:-2}"
ctest --test-dir "$BUILD" --output-on-failure
