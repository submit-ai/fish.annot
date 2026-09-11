# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all

SRC = os.path.normpath(os.path.join(SPECPATH, '..'))
# DLLs come from the environment PyInstaller itself runs in, so the spec carries
# no hard-coded path and builds on any machine.
_lib_bin = os.path.join(sys.prefix, 'Library', 'bin')

datas = [
    (os.path.join(SRC, 'config/species_config.json'), 'config'),
    (os.path.join(SRC, 'config/viewer_config.json'), 'config'),
    (os.path.join(SRC, 'assets/icon.ico'), 'assets'),
    (os.path.join(SRC, 'README.md'), '.'),
    (os.path.join(SRC, 'LICENSE'), '.'),
]
binaries = [
    (f'{_lib_bin}/ffi.dll',             '.'),
    (f'{_lib_bin}/ffi-7.dll',           '.'),
    (f'{_lib_bin}/ffi-8.dll',           '.'),
    (f'{_lib_bin}/libexpat.dll',         '.'),
    (f'{_lib_bin}/libcrypto-3-x64.dll',  '.'),
    (f'{_lib_bin}/libssl-3-x64.dll',     '.'),
    (f'{_lib_bin}/liblzma.dll',          '.'),
    (f'{_lib_bin}/libbz2.dll',           '.'),
]
hiddenimports = []
tmp_ret = collect_all('PySide6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('cv2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    [os.path.join(SRC, 'main.py')],
    pathex=[SRC],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'torchvision', 'torchaudio',
        'transformers', 'tokenizers', 'safetensors',
        'scipy', 'sklearn', 'matplotlib',
        'timm', 'huggingface_hub',
        'jedi', 'IPython', 'notebook',
        'lxml',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='fish_annot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(SRC, 'assets/icon.ico'),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='fish_annot',
)
