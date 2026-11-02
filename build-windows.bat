@echo off
setlocal
cd /d "%~dp0"

echo Building Remote Work Tracker for Windows...
echo.

REM Python 3.10+ must be installed (python.org or "py" launcher).
where py >nul 2>nul
if %errorlevel%==0 ( set "PY=py -3" ) else ( set "PY=python" )

if not exist .venv-build (
    echo Creating build environment .venv-build ...
    %PY% -m venv .venv-build || goto :error
)

call .venv-build\Scripts\activate.bat || goto :error
python -m pip install --upgrade pip || goto :error
pip install -r requirements-build.txt || goto :error

REM Optional: bundle the Gemini PDF fallback (adds roughly 50-100 MB).
REM   set RW_BUNDLE_GEMINI=1

echo.
echo Running tests...
python -m pytest -q -o addopts="" || goto :error

echo.
echo Running PyInstaller...
pyinstaller RemoteWorkTracker.spec --noconfirm --clean || goto :error

echo.
echo Build complete. Executable: dist\RemoteWorkTracker.exe
echo.
echo The state file tracker_state.json is created next to the exe on first start.
echo The program listens on 127.0.0.1:5000 only. Settings (optional):
echo   PORT, HOST, RW_NO_BROWSER=1, RW_DATA_FILE=C:\path\tracker_state.json
goto :end

:error
echo.
echo BUILD FAILED. See the messages above.
endlocal
pause
exit /b 1

:end
endlocal
pause
