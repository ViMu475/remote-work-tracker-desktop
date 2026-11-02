# Remote Work Tracker — Linux and Windows application

Local web application (Flask) that tracks working hours and checks the remote-work quota. It runs on your own
computer, shows its user interface in the browser (`http://127.0.0.1:5000`) and can be delivered as **one
program file**: `RemoteWorkTracker` for Linux and `RemoteWorkTracker.exe` for Windows. Nothing has to be installed
and no data leaves the computer (see [PRIVACY.md](PRIVACY.md)).

Sister project (Android and iOS, Kotlin Multiplatform): [remote-quota-guard](https://github.com/ViMu475/remote-quota-guard).

## How to get the program for each platform

| You want | Build on | Command | Result | Details |
|---|---|---|---|---|
| Run from source | Linux, macOS, Windows | `python app.py` | browser opens at `http://127.0.0.1:5000` | [BUILDING.md](BUILDING.md#run-from-source) |
| **Linux program** | Linux | `./build.sh` | `dist/RemoteWorkTracker` | [BUILDING.md](BUILDING.md#linux-program) |
| **Windows EXE** | Windows | `build-windows.bat` | `dist\RemoteWorkTracker.exe` | [BUILDING.md](BUILDING.md#windows-exe-on-windows) |
| **Both, without your own machine** | GitHub Actions | workflow `Build desktop apps` | artifacts `RemoteWorkTracker-Linux`, `RemoteWorkTracker-Windows` | [BUILDING.md](BUILDING.md#github-actions-linux-and-windows-in-the-cloud) |
| **Windows EXE on a Linux PC** | Linux with Wine | `bash tools/wine/build-exe-with-wine.sh` | `dist-wine/RemoteWorkTracker.exe` | [BUILDING.md](BUILDING.md#windows-exe-on-linux-with-wine) |

PyInstaller cannot cross-compile: the Windows EXE has to be built on Windows (real or in the cloud) or with
Wine, the Linux program on Linux. After every build, `python tools/smoke_test.py <program>` checks that the
program really works.

*Deutsch, kurz:* Linux-Programm mit `./build.sh`, Windows-EXE mit `build-windows.bat` auf einem Windows-PC,
beides ohne eigenen Rechner über GitHub Actions, die Windows-EXE alternativ auf Linux mit Wine
(`tools/wine/build-exe-with-wine.sh`). Prüfen: `python tools/smoke_test.py <Programm>`. Alle Schritte stehen in
[BUILDING.md](BUILDING.md). **Datenschutz:** In dieses Repository gehören keine Zeitnachweise, PDFs, Screenshots oder
Zustandsdateien, siehe [PRIVACY.md](PRIVACY.md).

## Quick start (from source)

```bash
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py                       # http://127.0.0.1:5000
```

Settings (environment variables, all optional): `PORT` (default 5000), `HOST` (default `127.0.0.1`, the program
listens on the local computer only), `RW_NO_BROWSER=1` (do not open the browser), `RW_DATA_FILE` (where the state file
lives), `RW_DEBUG=1` (Flask debugger, only on the local computer), `GOOGLE_API_KEY` (optional PDF fallback, see
[PRIVACY.md](PRIVACY.md)). The data is stored in `tracker_state.json` (next to the program file, or in the
working directory when run from source).

## Features

- Record working time (date, start, end, break, remote hours), edit, delete, overlap detection, break rules (ArbZG)
- Monthly overview with soll hours, remote limit and quota; choose any month to look at
- Close a month into the **history**: sorted, months over the remote limit have a **red background**
- **Final report** by quarter with rating (up to 90 % of the limit good, up to 100 % tight, above exceeded)
- Quarterly automatic quota adjustment (±10 %), Bavarian holidays 2025–2030
- Import of SAP time statements (PDF), CSV and PDF monthly report, JSON backup and restore
- German and English, dark mode

## Tests

```bash
pip install -r requirements.txt
python -m pytest -q
python tools/check_privacy.py       # privacy guard, also part of the test suite and of CI
```

The suite (about 400 tests) uses only fictional data; tests that need real statements are skipped unless you provide them locally (see PRIVACY.md). Long-running model tests: `RW_SOAK_STEPS=1500
RW_SOAK_SEEDS=20 python -m pytest tests/test_soak.py -k random_run`. Browser checks (Playwright) are described in
[BUILDING.md](BUILDING.md#browser-checks).

## Project structure

```
app.py, config.py            start-up, settings, holidays and quarter tables
routes/api.py                HTTP API (/api/...)
services/                    calculation, state file, PDF import, reports, final report
templates/, static/          user interface (single page)
tests/                       pytest suite, model-based long-run tests, browser checks
tools/                       smoke_test.py, check_privacy.py, wine/build-exe-with-wine.sh
RemoteWorkTracker.spec       PyInstaller configuration
build.sh, build-windows.bat  one-command builds
.github/workflows/         GitHub Actions: Linux and Windows builds in the cloud
```

## License

MIT, see [LICENSE](LICENSE).
