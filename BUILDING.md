# Building the Linux and Windows program

The application is a Flask program. [PyInstaller](https://pyinstaller.org) packs it with Python and all
libraries into **one file** (`RemoteWorkTracker` on Linux, `RemoteWorkTracker.exe` on Windows). The recipe is
[`RemoteWorkTracker.spec`](RemoteWorkTracker.spec).

## Which way is the right one?

PyInstaller does not cross-compile: it builds for the system it runs on. That gives four ways:

| Way | When to choose it | Effort |
|---|---|---|
| **GitHub Actions** (recommended) | You want both files without touching your own machine; every push is tested and built the same way | none (see below) |
| **Linux build** (`build.sh`) | You are on Linux and want the Linux program | one command |
| **Windows build** (`build-windows.bat`) | You have a Windows PC | one command |
| **Windows EXE on Linux with Wine** | You only have Linux but need an EXE right now | one-time preparation (~1.5 GB), then one command |

Every way ends the same: run the tests, run PyInstaller, then check the program with
`python tools/smoke_test.py <program>` (starts it with a throw-away data file, imports fictional entries, closes a month,
reads the final report and shuts it down through the protected endpoint).

## Run from source

```bash
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py                       # http://127.0.0.1:5000
```

Python 3.10 or newer (3.12 is what the builds use). Optional settings: `PORT`, `HOST` (default `127.0.0.1`),
`RW_NO_BROWSER=1`, `RW_DATA_FILE=<path of the state file>`, `RW_DEBUG=1` (local computer only).

## Linux program

```bash
python3 -m venv .venv-build
source .venv-build/bin/activate
pip install -r requirements-build.txt
PYTHON=python ./build.sh            # tests, then PyInstaller
python tools/smoke_test.py dist/RemoteWorkTracker
```

Result: `dist/RemoteWorkTracker` (about 40 MB, runs on Linux systems with a similar or newer glibc than the build
machine). Start it with `./dist/RemoteWorkTracker`; the browser opens, the state file `tracker_state.json` is created
next to the program.

## Linux packages (.deb and .rpm)

From the finished Linux program `packaging/linux/build-packages.sh` builds a Debian/Ubuntu package and an RPM for
Fedora/RHEL/openSUSE:

```bash
sudo apt install fakeroot rpm            # dpkg-deb comes with Debian/Ubuntu; rpmbuild is in the package "rpm"
packaging/linux/build-packages.sh dist/RemoteWorkTracker 1.1.1 dist-packages
```

Result: `remote-work-tracker_<version>_amd64.deb` and `remote-work-tracker-<version>-1.x86_64.rpm`. Both install the
program to `/opt/remote-work-tracker`, a start command `remote-work-tracker`, a menu entry and an icon. The start
command keeps the state file in the user's own folder (`~/.local/share/remote-work-tracker/tracker_state.json`),
because `/opt` is not writable for normal users. The packages need a glibc at least as new as the one of the build
machine (the GitHub build uses an older Ubuntu, so its packages run on more systems). They are not signed.

## Windows EXE on Windows

Install Python 3.10 or newer from python.org (tick "py launcher"), then in the project folder:

```bat
build-windows.bat
python tools\smoke_test.py dist\RemoteWorkTracker.exe
```

The script creates `.venv-build`, installs `requirements-build.txt`, runs the tests and PyInstaller. Result:
`dist\RemoteWorkTracker.exe` (about 38 MB, console window with the address, stop with Ctrl+C). Windows
SmartScreen may warn about an unsigned program ("More info" → "Run anyway"); signing needs a code-signing certificate.

## GitHub Actions: Linux and Windows in the cloud

The workflow [`.github/workflows/build-desktop.yml`](.github/workflows/build-desktop.yml) does, on an Ubuntu and a Windows runner: privacy check →
tests → PyInstaller → smoke test → upload of the program as an artifact (`RemoteWorkTracker-Linux`,
`RemoteWorkTracker-Windows`). The Linux job also builds the `.deb` and `.rpm` (artifact `RemoteWorkTracker-Linux-packages`).

It runs on every push and pull request to `main`. Pushing workflow files needs a Git token with the `workflow`
scope (`gh auth refresh -s workflow`). To run it manually use *Actions → Build desktop apps → Run workflow*, then download
the artifacts from the run page. Option "bundle_gemini" builds the larger variant with the optional Gemini PDF fallback
(see [PRIVACY.md](PRIVACY.md); off by default).

## Windows EXE on Linux with Wine

No Windows PC needed, no root: the real Windows Python and PyInstaller run under Wine and produce a genuine
Windows executable (PE32+, x86-64). The build is fully offline after the preparation.

### One-time preparation (about 1.5 GB in `~/dev-tools`)

```bash
mkdir -p ~/dev-tools/dl && cd ~/dev-tools

# 1. Wine 11.0 (Kron4ek build). Compare the SHA-256 with the value in the release notes on GitHub.
curl -L -o dl/wine-11.0-amd64.tar.xz \
  https://github.com/Kron4ek/Wine-Builds/releases/download/11.0/wine-11.0-amd64.tar.xz
sha256sum dl/wine-11.0-amd64.tar.xz
tar -xf dl/wine-11.0-amd64.tar.xz

# 2. Windows Python 3.12.10 (NuGet package of the Python Software Foundation).
#    Compare the hash with the one shown on https://www.nuget.org/packages/python/3.12.10
curl -L -o dl/python.3.12.10.nupkg \
  https://api.nuget.org/v3-flatcontainer/python/3.12.10/python.3.12.10.nupkg

# 3. The Windows wheels of all packages (62 files). "pip download" on Linux skips packages that only exist on
#    Windows, so colorama, pefile and pywin32-ctypes are listed explicitly.
python3 -m venv /tmp/dl-env && /tmp/dl-env/bin/python -m pip install --upgrade pip
/tmp/dl-env/bin/python -m pip download --dest winwheels \
  --platform win_amd64 --python-version 3.12 --implementation cp --abi cp312 --only-binary=:all: \
  -r /path/to/this/repo/requirements-build.txt colorama pefile pywin32-ctypes pip setuptools wheel

# 4. Environment file used by the build script
cat > wine-env.sh <<'ENVEOF'
export WINE_HOME="$HOME/dev-tools/wine-11.0-amd64"
export PATH="$WINE_HOME/bin:$PATH"
export WINEPREFIX="$HOME/dev-tools/wineprefix"
export WINEARCH=win64
export WINEDEBUG=-all
export WINEDLLOVERRIDES="mscoree,mshtml="   # no Mono/Gecko download prompts
ENVEOF
```

### Build

```bash
bash tools/wine/build-exe-with-wine.sh        # add --skip-tests to skip the Windows-Python tests
```

The script creates the Wine prefix and unpacks Python (first run only), installs the wheels offline, copies the sources
(never `.env`, state files, PDFs or `docs/`), runs the tests with the Windows Python, builds the EXE and smoke-tests it
under Wine. Result: `dist-wine/RemoteWorkTracker.exe` and `dist-wine/SHA256SUMS.txt`. Set `DEV=<folder>` if the
preparation lives elsewhere than `~/dev-tools`.

A Wine build is a good check, but it is **not** a test on real Windows: before handing the EXE to other people also run it
once on a Windows PC (SmartScreen, antivirus, write permission next to the file).

## Rebuild the CSS

The web interface uses a **local** stylesheet, `static/css/app.css` (no CDN, works offline). It is generated with the
[Tailwind CSS](https://tailwindcss.com) command line tool (version 3.4.17) from `tailwind-input.css`
(design tokens and components) and `tailwind.config.js` (which files are scanned for class names). Only the
generated file is part of the program; Node.js is needed only when you change classes or colours:

```bash
mkdir -p /tmp/tw && cd /tmp/tw && npm init -y && npm install tailwindcss@3.4.17   # once, outside the repository
cd <repository>
/tmp/tw/node_modules/.bin/tailwindcss -c tailwind.config.js -i tailwind-input.css -o static/css/app.css --minify
```

Classes that `static/js/app.js` assembles from parts (for example `toast-${type}`) must be listed in the `safelist`
of `tailwind.config.js`. `tests/test_design_tokens.py` checks the WCAG contrast of the colour tokens in the result.

## Build options

| Variable (at build time) | Effect |
|---|---|
| `RW_BUNDLE_GEMINI=1` | also bundle `google-generativeai` (Gemini PDF fallback, +50–100 MB). Default: not included. |

Never bundled: `.env`, `tracker_state.json`, tests, documentation.

## Tests

```bash
python -m pytest -q                    # about 400 tests with fictional data (the privacy guard is part of it)
RW_SOAK_STEPS=1500 RW_SOAK_SEEDS=20 python -m pytest tests/test_soak.py -k random_run   # long-run model test, ~9 min
```

### Browser checks

Playwright scripts (not part of pytest) drive the real user interface with fictional data:

```bash
pip install playwright && playwright install chromium
RW_APP_PYTHON=python python tests/browser/verify_history_report.py . [screenshot-folder]
RW_APP_PYTHON=python python tests/browser/verify_view_restore.py .
pip install reportlab        # the next check makes its fictional statements itself
RW_APP_PYTHON=python python tests/browser/verify_batch_import.py . [screenshot-folder]
```

`RW_APP_PYTHON` is the Python of the environment where Flask is installed (default `python3`).

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `build.sh`: "PyInstaller is missing" | install `requirements-build.txt` in the Python you pass as `PYTHON` |
| Windows: `py` or `python` not found | install Python from python.org and tick the launcher / "Add to PATH" |
| Smoke test: "the program does not answer" | port 5055 busy: `SMOKE_PORT=5077 python tools/smoke_test.py ...`; antivirus blocking the new EXE |
| Wine build: `MISSING: ...` | the one-time preparation is incomplete (the message names the file) |
| pip under Wine: missing package | the wheel list is incomplete: repeat step 3 of the preparation |
| `check_privacy.py` reports a file | remove it from the repository, see [PRIVACY.md](PRIVACY.md) |
