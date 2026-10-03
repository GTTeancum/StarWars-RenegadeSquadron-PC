#!/bin/bash
set -euo pipefail
cmake -S '/mnt/data/renegade/independent005/source' -B '/mnt/data/renegade/independent005/final-build' -G Ninja -DCMAKE_BUILD_TYPE=Release -DPSPRECOMP_PROFILE=renegade -DRENEGADE_DISC_ROOT='/mnt/data/renegade/game/disc' -DRENEGADE_PREBUILT_AOT='/mnt/data/renegade/prebuilt/linux-x86_64/librenegade_aot.a' -DRENEGADE_AOT_BINDING='/mnt/data/renegade/tools/aot-binding004.json' -DRENEGADE_AOT_VERIFIER='/mnt/data/renegade/tools/verify_aot004.py' -DRENEGADE_SDK='/mnt/data/renegade/intake/sdk'
cmake --build '/mnt/data/renegade/independent005/final-build' --parallel 2
ctest --test-dir '/mnt/data/renegade/independent005/final-build' --verbose
sha256sum '/mnt/data/renegade/independent005/final-build/bin/RenegadeNative' '/mnt/data/renegade/intake/out/native004/bin/RenegadeNative'
