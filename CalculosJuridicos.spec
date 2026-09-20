# -*- mode: python ; coding: utf-8 -*-
import os
import runpy
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VSVersionInfo,
    VarFileInfo,
    VarStruct,
)

project = Path(SPECPATH)
backend = project / "backend"
identity = runpy.run_path(str(backend / "liquidacao_custom/metadata.py"))
version = tuple(int(part) for part in identity["APP_VERSION"].split("."))
version_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=version,
        prodvers=version,
        mask=0x3F,
        flags=0,
        OS=0x40004,
        fileType=1,
        subtype=0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo([
            StringTable("041604B0", [
                StringStruct("CompanyName", "Barreto Fontes Advocacia"),
                StringStruct("FileDescription", identity["APP_NAME"]),
                StringStruct("ProductName", identity["APP_NAME"]),
                StringStruct("FileVersion", identity["APP_VERSION"]),
                StringStruct("ProductVersion", identity["APP_DISPLAY_VERSION"]),
                StringStruct("OriginalFilename", identity["EXECUTABLE_NAME"]),
            ])
        ]),
        VarFileInfo([VarStruct("Translation", [0x0416, 1200])]),
    ],
)

datas = [
    (str(backend / "data"), "data"),
    (str(backend / "liquidacao_custom/assets"), "liquidacao_custom/assets"),
    (str(backend / "liquidacao_custom/web"), "liquidacao_custom/web"),
    (
        str(backend / "liquidacao_custom/updates/install-update.ps1"),
        "liquidacao_custom/updates",
    ),
    (str(project / "build/calculos-juridicos.ico"), "liquidacao_custom/assets"),
]

a = Analysis(
    [str(project / "desktop_main.py")],
    pathex=[str(backend)],
    binaries=[],
    datas=datas,
    hiddenimports=collect_submodules("webview"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CalculosJuridicos",
    version=version_info,
    icon=str(project / "build/calculos-juridicos.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=os.environ.get("CALCULOS_BUILD_CONSOLE") == "1",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CalculosJuridicos",
)
