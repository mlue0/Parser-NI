# -*- mode: python ; coding: utf-8 -*-
"""
SimpleMeasure — PyInstaller spec.
Сборка: pyinstaller SimpleMeasure.spec  (или запустить build.bat)
"""

from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH)

# Данные для включения в сборку
added_datas = [
    (str(ROOT / 'config' / 'fields_config.json'), 'config'),
]
for src, dst in [
    (str(ROOT / '.env.example'), '.'),
    (str(ROOT / 'config' / 'fields_config.default.json'), 'config'),
]:
    if Path(src).exists():
        added_datas.append((src, dst))

a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=added_datas,
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtPrintSupport',
        'pydantic',
        'pydantic_core',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'xlrd',
        'pandas',
        'keyring',
        'keyring.backends',
        'keyring.backends.Windows',
        'dotenv',
        'requests',
        'urllib3',
        'charset_normalizer',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'pytest_qt', 'tkinter', 'matplotlib', 'scipy', 'IPython'],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SimpleMeasure',
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
    icon=None,
)
