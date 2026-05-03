# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for py-autoclick — single-file, GUI-mode, multi-OS.

Driven by .github/workflows/release.yml at tag time. Produces:
  - Linux:   ./dist/pyautoclick                 (ELF binary)
  - Windows: ./dist/pyautoclick.exe              (PE binary, no console)
  - macOS:   ./dist/PyAutoClick.app              (.app bundle, no console)

Local build (any OS):
    pip install pyinstaller>=6.0
    pyinstaller pyautoclick.spec --clean --noconfirm
"""

from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

PROJECT_ROOT = Path(SPECPATH)
ASSETS_DIR = PROJECT_ROOT / "pyautoclick" / "assets"

# Bundle the locale JSONs and the icon — both are loaded via importlib.resources
# at runtime, so PyInstaller must be told they're not source code.
datas: list[tuple[str, str]] = []
datas += collect_data_files("pyautoclick.assets", includes=["*.png"])
datas += collect_data_files("pyautoclick.i18n.locales", includes=["*.json"])

# Pynput dynamically imports its platform backend from a string at runtime.
# PyInstaller's static analysis cannot follow that, so we collect every
# pynput submodule explicitly. Same for sv_ttk's TCL files.
hiddenimports: list[str] = []
hiddenimports += collect_submodules("pynput")
hiddenimports += collect_submodules("sv_ttk")
datas += collect_data_files("sv_ttk")

# Icon: PNG works on Linux directly. Windows wants .ico, macOS wants .icns;
# without those, PyInstaller falls back to the default icon (acceptable for
# v0.3.3 — proper icons can be added later without changing the spec).
ICON_PATH = ASSETS_DIR / "py-autoclick.png"
icon_arg = str(ICON_PATH) if ICON_PATH.exists() else None


a = Analysis(
    ["pyautoclick/__main__.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter.test", "test", "unittest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="pyautoclick",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # GUI app — no console window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,        # native arch (arm64 on Apple Silicon runners)
    codesign_identity=None,  # no signing in CI for now
    entitlements_file=None,
    icon=icon_arg,
)


# macOS: wrap the binary in a proper .app bundle so it can be double-clicked
# from Finder. The Info.plist declares the Accessibility usage string that
# macOS requires when the app asks for global input capture.
if sys.platform == "darwin":
    app = BUNDLE(  # noqa: F841 — picked up by PyInstaller via the global
        exe,
        name="PyAutoClick.app",
        icon=icon_arg,
        bundle_identifier="com.thomasmayor.pyautoclick",
        info_plist={
            "CFBundleShortVersionString": "0.3.5",
            "NSHighResolutionCapable": "True",
            "NSAccessibilityUsageDescription": (
                "PyAutoClick needs Accessibility permission to capture global "
                "hotkeys and mouse events."
            ),
        },
    )
