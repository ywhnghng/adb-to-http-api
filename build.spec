# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller build specification for the ADB HTTP API server.
#
# Build on Python 3.11 (locked for the released exe) with:
#     pyinstaller build.spec
# Output: dist/main.exe  (onefile, windowed)
#
# NOTE: The official release target is Python 3.11. Building on other
# versions (e.g. 3.13) will produce a working but version-mismatched exe.

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[('docs/AGENT_API_GUIDE.md', 'docs')],
    hiddenimports=[
        "pystray",
        "pystray._win32",
        "tkinter",
        "PIL",
        "PIL.Image",
        "win32api",
        "win32gui",
        "win32con",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="main",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # --windowed: no console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="app.ico",       # optional: uncomment if an icon file is provided
)
