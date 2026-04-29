"""Resource path resolution for both source and PyInstaller-frozen runtimes."""

import sys
from pathlib import Path


def get_resource_root() -> Path:
    """Root for bundled resources.

    Source mode: project root (parent of src/).
    PyInstaller frozen mode (--onefile): sys._MEIPASS (extracted bundle).
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


def get_icon_path() -> Path:
    """Path to the application .ico icon."""
    return get_resource_root() / "assets" / "icons" / "icone.ico"


def get_dlib_model_path() -> Path:
    """Path to the dlib shape predictor model."""
    return get_resource_root() / "assets" / "shape_predictor_68_face_landmarks.dat"
