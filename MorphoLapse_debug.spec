# -*- mode: python ; coding: utf-8 -*-
"""
MorphoLapse - Configuration PyInstaller DEBUG
Executable avec console pour diagnostic
"""

import os
import sys
from pathlib import Path

ROOT = Path(SPECPATH)

# Liste complete des exclusions pour alleger l'executable
EXCLUDES = [
    # Machine Learning / Deep Learning (non utilises)
    'tensorflow',
    'tensorflow_core',
    'tensorflow_estimator',
    'tensorboard',
    'keras',
    'torch',
    'torchvision',
    'torchaudio',
    'transformers',
    'sklearn',
    'scikit-learn',

    # Data Science (non utilises)
    'pandas',
    'matplotlib',
    'seaborn',
    'plotly',
    'bokeh',

    # Jupyter / IPython
    'IPython',
    'jupyter',
    'jupyter_client',
    'jupyter_core',
    'notebook',
    'ipykernel',
    'ipywidgets',

    # Tests et dev
    'pytest',
    'unittest',
    'nose',
    'coverage',
    'sphinx',
    'docutils',

    # Autres non necessaires
    'PyQt5',
    'PyQt6',
    'PySide2',
    'PySide6',
    'wx',
    'kivy',
    'pyglet',
    'pygame',
    'pyarrow',
    'numba',
    'llvmlite',
    'h5py',
    'grpc',
    'grpcio',
    'google',
    'google-cloud',
    'boto3',
    'botocore',
    'azure',
    'cryptography',
    'paramiko',
    'fabric',
]

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
        'scipy.spatial.distance',
        'numpy',
        'cv2',
        'dlib',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.ttk',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
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
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # Console activee pour debug
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
