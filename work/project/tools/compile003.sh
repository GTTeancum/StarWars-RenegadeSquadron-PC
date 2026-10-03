#!/bin/bash
set -euo pipefail
R=/mnt/data/renegade
S="$R/intake/sources/PSPRecomp"
cmake --build "$R/intake/out/framework" --parallel 2
ctest --test-dir "$R/intake/out/framework" --output-on-failure
bash "$R/tools/generate003.sh"
cmake -S "$S" -B "$R/intake/out/renegade" -G Ninja -DPSPRECOMP_PROFILE=renegade -DCMAKE_BUILD_TYPE=Release
cmake --build "$R/intake/out/renegade" --target RenegadeNative --parallel 3
