#!/bin/bash
# Build the stand-alone executable for THIS system (Linux/macOS).
# For Windows use build-windows.bat on a Windows PC or the GitHub workflow.
#
#   PYTHON=/path/to/python ./build.sh     # python with requirements-build.txt installed
#   RW_BUNDLE_GEMINI=1 ./build.sh         # also bundle the Gemini PDF fallback
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"

if ! "$PYTHON" -c "import PyInstaller" 2>/dev/null; then
    echo "PyInstaller is missing for $PYTHON."
    echo "Install first:  $PYTHON -m pip install -r requirements-build.txt"
    exit 1
fi

"$PYTHON" -m pytest -q -o addopts=""
"$PYTHON" -m PyInstaller RemoteWorkTracker.spec --noconfirm --clean "$@"

echo
echo "Build complete: dist/RemoteWorkTracker"
