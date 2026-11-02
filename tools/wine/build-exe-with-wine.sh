#!/bin/bash
# Builds RemoteWorkTracker.exe (a real Windows executable) on Linux with Wine - no root, no Windows PC.
#
# One-time preparation (see BUILDING.md, section "Windows EXE on Linux with Wine"):
#   $DEV/wine-<version>-amd64/   Wine (Kron4ek build)         -> wine-env.sh below points to it
#   $DEV/dl/python.3.12.10.nupkg official CPython for Windows  (NuGet package of the Python Software Foundation)
#   $DEV/winwheels/              Windows wheels of requirements-build.txt (pip download --platform win_amd64)
#
# Usage:   bash tools/wine/build-exe-with-wine.sh [--skip-tests]
# Result:  $OUT/RemoteWorkTracker.exe (default: <repo>/dist-wine/) and SHA256SUMS.txt
# Env:     DEV (default ~/dev-tools), OUT, WINE_ENV (default $DEV/wine-env.sh)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEV="${DEV:-$HOME/dev-tools}"
OUT="${OUT:-$REPO/dist-wine}"
WHEELS="$DEV/winwheels"
NUPKG="$DEV/dl/python.3.12.10.nupkg"

# wine-env.sh sets WINE_HOME, PATH, WINEPREFIX, WINEARCH=win64, WINEDEBUG=-all and disables Mono/Gecko prompts
# shellcheck disable=SC1090
source "${WINE_ENV:-$DEV/wine-env.sh}"

for f in "$WINE_HOME/bin/wine" "$NUPKG" "$REPO/RemoteWorkTracker.spec" "$WHEELS"; do
  [ -e "$f" ] || { echo "MISSING: $f (see BUILDING.md, preparation)"; exit 1; }
done

C="$WINEPREFIX/drive_c"
PYDIR="$C/python312"
WORK="$C/build/src"
WPY='C:\python312\python.exe'
step() { echo; echo "== $*"; }

step "1/7 create the Wine prefix (once)"
[ -f "$C/windows/system32/kernel32.dll" ] || wine wineboot -u
wine --version

step "2/7 unpack Windows Python 3.12.10 (once)"
if [ ! -f "$PYDIR/python.exe" ]; then
  tmp="$(mktemp -d)"
  unzip -q "$NUPKG" 'tools/*' -d "$tmp"
  mkdir -p "$PYDIR"
  cp -a "$tmp/tools/." "$PYDIR/"
  rm -rf "$tmp"
fi
wine "$WPY" --version

step "3/7 install the packages offline (pip, PyInstaller, Flask, pdfplumber, ...)"
WW="$(winepath -w "$WHEELS")"
wine "$WPY" -m ensurepip --default-pip > /dev/null
wine "$WPY" -m pip install --no-index --find-links "$WW" --upgrade pip setuptools wheel
wine "$WPY" -m pip install --no-index --find-links "$WW" -r "$(winepath -w "$REPO/requirements-build.txt")"

step "4/7 copy the sources into the build folder (without local or private files)"
rm -rf "$WORK"
mkdir -p "$WORK"
tar -C "$REPO" \
  --exclude='./.git' --exclude='./dist' --exclude='./dist-wine' --exclude='./build' --exclude='./docs' \
  --exclude='./.env*' --exclude='./tracker_state*.json' --exclude='./tests/real_statements' \
  --exclude='*.pdf' --exclude='__pycache__' --exclude='./.venv*' --exclude='./venv' -cf - . | tar -C "$WORK" -xf -
cd "$WORK"

step "5/7 tests with the Windows Python (under Wine)"
if [ "${1:-}" = "--skip-tests" ]; then
  echo "(skipped)"
else
  wine "$WPY" -m pytest -q -o addopts= -p no:cacheprovider
fi

step "6/7 PyInstaller builds RemoteWorkTracker.exe"
wine "$WPY" -m PyInstaller RemoteWorkTracker.spec --noconfirm --clean
EXE="$WORK/dist/RemoteWorkTracker.exe"
[ -f "$EXE" ] || { echo "The build produced no EXE."; exit 1; }
mkdir -p "$OUT"
cp -p "$EXE" "$OUT/RemoteWorkTracker.exe"
file "$OUT/RemoteWorkTracker.exe" || true

step "7/7 smoke test of the EXE under Wine"
python3 "$REPO/tools/smoke_test.py" -- wine "$OUT/RemoteWorkTracker.exe"
wineserver -k 2> /dev/null || true

(cd "$OUT" && sha256sum RemoteWorkTracker.exe | tee SHA256SUMS.txt)
echo
echo "DONE: $OUT/RemoteWorkTracker.exe"
