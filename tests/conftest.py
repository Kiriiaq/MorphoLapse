"""Shared pytest fixtures for MorphoLapse tests."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _reset_logger_singleton():
    """Logger is a process-wide singleton; reset between tests so each can
    construct one with isolated state (callbacks, log dir)."""
    from src.utils.logger import Logger
    Logger._instance = None
    yield
    Logger._instance = None


@pytest.fixture
def synthetic_image():
    """Synthetic 100x100 BGR image with a centered grey square."""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[40:60, 40:60] = 128
    return img


@pytest.fixture
def temp_image_dir(tmp_path, synthetic_image):
    """Temp dir with 3 valid PNG images named 000.png .. 002.png."""
    import cv2
    for i in range(3):
        cv2.imwrite(str(tmp_path / f"{i:03d}.png"), synthetic_image)
    return tmp_path


@pytest.fixture
def temp_config_path(tmp_path):
    return str(tmp_path / "config.json")
