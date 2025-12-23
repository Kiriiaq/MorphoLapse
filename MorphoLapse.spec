# -*- mode: python ; coding: utf-8 -*-
"""
MorphoLapse - Executable UNIQUE (onefile)
Double-clic pour lancer, sans console
"""

import os
import sys
from pathlib import Path

ROOT = Path(SPECPATH)

EXCLUDES = [
    'tensorflow', 'tensorflow_core', 'tensorflow_estimator', 'tensorboard',
    'keras', 'torch', 'torchvision', 'torchaudio', 'transformers',
    'sklearn', 'scikit-learn', 'pandas', 'matplotlib', 'seaborn', 'plotly',
    'IPython', 'jupyter', 'jupyter_client', 'jupyter_core', 'notebook',
    'pytest', 'unittest', 'nose', 'coverage', 'sphinx', 'docutils',
    'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'wx', 'kivy', 'pyglet', 'pygame',
    'pyarrow', 'numba', 'llvmlite', 'h5py', 'grpc', 'grpcio',
    'google', 'boto3', 'botocore', 'azure', 'cryptography', 'paramiko',
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
        'PIL', 'PIL._tkinter_finder', 'PIL.Image', 'PIL.ImageTk',
        'scipy.spatial', 'scipy.spatial.transform', 'scipy.spatial._qhull',
        'numpy', 'cv2', 'dlib',
        'tkinter', 'tkinter.filedialog', 'tkinter.messagebox',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=EXCLUDES,
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
    name='MorphoLapse',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    icon='ico/icone.ico',
)
