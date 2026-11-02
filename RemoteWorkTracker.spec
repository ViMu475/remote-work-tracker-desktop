# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Remote Work Tracker.

Build:   pyinstaller RemoteWorkTracker.spec --noconfirm --clean
Result:  dist/RemoteWorkTracker.exe (Windows) or dist/RemoteWorkTracker (Linux/macOS)

PyInstaller builds for the system it runs on, so the .exe must be built on
Windows (see build-windows.bat or .github/workflows/build-windows.yml).

Options (environment variables at build time):
  RW_BUNDLE_GEMINI=1   also bundle google-generativeai (Gemini PDF fallback,
                       adds roughly 50-100 MB). Without it the exe parses SAP
                       time statements locally with pdfplumber only.

Never bundled: .env (API keys), tracker_state.json (user data), tests, docs.
"""
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(SPECPATH)  # noqa: F821  (SPECPATH is provided by PyInstaller)

datas = [
    (os.path.join(ROOT, 'templates'), 'templates'),
    (os.path.join(ROOT, 'static'), 'static'),
]
datas += collect_data_files('pdfminer')    # CMap resources used by pdfplumber
datas += collect_data_files('reportlab')   # fonts for the PDF report

hiddenimports = []
hiddenimports += collect_submodules('pdfplumber')
hiddenimports += collect_submodules('pdfminer')
hiddenimports += collect_submodules('reportlab')

excludes = [
    'pytest', '_pytest', 'pytest_cov', 'coverage', 'freezegun',
    'tkinter', 'IPython', 'matplotlib', 'numpy.tests',
]

if os.environ.get('RW_BUNDLE_GEMINI') == '1':
    hiddenimports += collect_submodules('google.generativeai')
    datas += collect_data_files('google.generativeai')
else:
    excludes += ['google.generativeai', 'google.ai', 'grpc']

a = Analysis(  # noqa: F821
    [os.path.join(ROOT, 'app.py')],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='RemoteWorkTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    # A console window shows the address and lets the user stop the app with
    # Ctrl+C; a windowed build has no stdout/stderr and hides errors.
    console=True,
)
