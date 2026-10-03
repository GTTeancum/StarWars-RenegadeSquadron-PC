#!/usr/bin/env bash
# Linux scratch launcher. Windows is not verified.
set -euo pipefail
if [[ "$#" -ne 2 ]]; then
  echo "Usage: $0 /path/to/BOOT.BIN /path/to/extracted-disc-root" >&2
  exit 2
fi
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
EXE="${RENEGADE_EXECUTABLE:-$ROOT/prebuilt/linux-x86_64/RenegadeNative}"
[[ -x "$EXE" ]] || { echo "Native Linux executable missing or not executable: $EXE" >&2; exit 2; }
export RENEGADE_CONTROLS=modern
exec "$EXE" "$1" "$2" "${RENEGADE_DISPATCH_BUDGET:-2000000000}"
