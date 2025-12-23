# -*- mode: python ; coding: utf-8 -*-
"""
MorphoLapse - Configuration PyInstaller (Production)
Executable sans console, optimise pour l'utilisateur final
"""

import os
import sys
from pathlib import Path

# Chemin racine du projet
ROOT = Path(SPECPATH)

a = Analysis(
    ['main_app.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('ico/icone.ico', 'ico'),
        ('shape_predictor_68_face_landmarks.dat', '.'),
    ],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL._tkinter_finder',
        'PIL.Image',
        'PIL.ImageTk',
        'scipy.spatial',
        'scipy.spatial.transform',
        'scipy.spatial._qhull',
        'numpy',
        'numpy.core._methods',
        'numpy.lib.format',
        'cv2',
        'dlib',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'pandas',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'sphinx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MorphoLapse',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Pas de console en production
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ico/icone.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MorphoLapse',
)
