# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for InvoiceReceiptParser.exe standalone Windows binary."""

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

rapidocr_datas = collect_data_files("rapidocr_onnxruntime")
onnx_binaries = collect_dynamic_libs("onnxruntime")

datas = [
    ("assets/app_icon.ico", "assets"),
] + rapidocr_datas

hiddenimports = [
    "fitz",
    "pymupdf",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageTk",
    "numpy",
    "rapidocr_onnxruntime",
    "onnxruntime",
    "cv2",
    "pyclipper",
    "shapely",
    "dotenv",
]

a = Analysis(
    ["src/main.py"],
    pathex=["."],
    binaries=onnx_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="InvoiceReceiptParser",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/app_icon.ico",
)
