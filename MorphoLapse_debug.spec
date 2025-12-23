# -*- mode: python ; coding: utf-8 -*-
"""
MorphoLapse - Configuration PyInstaller (Debug)
Executable avec console pour le debogage et les logs detailles
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
    name='MorphoLapse_debug',
    debug=True,  # Mode debug active
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Pas de compression pour faciliter le debogage
    console=True,  # Console activee pour voir les logs
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
    upx=False,
    upx_exclude=[],
    name='MorphoLapse_debug',
)
