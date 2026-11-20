#!/usr/bin/env bash
# Start LTspice (Wine) on the X display, inside fmcw3-sim. Used by `./run --sim-gui ltspice [file]`.
# The baked prefix belongs to root and Wine insists the prefix is owned by the caller, so build a
# per-run dir of symlinks into it (as tests/sim/ltspice_smoke.py does).
set -euo pipefail
BAKED=${LTSPICE_PREFIX:-/opt/wineprefix}

args=()
if [ $# -gt 0 ]; then
  f=$(realpath -e "$1") || { echo "ltspice: no such file: $1" >&2; exit 1; }
  case $f in /work/*) ;; *) echo "ltspice: file must be inside the repo: $1" >&2; exit 1 ;; esac
  [ -f "$f" ] || { echo "ltspice: not a file: $1" >&2; exit 1; }
  args=("Z:${f//\//\\}")
fi

pre=$(mktemp -d /tmp/wineprefix.XXXXXX)
for p in "$BAKED"/* "$BAKED"/.[!.]*; do
  [ -e "$p" ] && ln -s "$p" "$pre/$(basename "$p")"
done
export WINEPREFIX=$pre WINEDEBUG=-all USER=root

wine 'C:\Program Files\ADI\LTspice\LTspice.exe' "${args[@]}" || true
wineserver -w || true
rm -rf "$pre"
