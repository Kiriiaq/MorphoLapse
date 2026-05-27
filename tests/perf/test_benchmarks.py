"""Micro-benchmarks for hot paths.

On utilise time.perf_counter (pas de pytest-benchmark requis). Les seuils
sont larges pour ne pas casser sur CI lente, mais ils détectent une
régression x10.
"""

import time

import numpy as np
import pytest
from src.modules.step_morph import get_blend_mode, get_easing_function
from src.utils.file_utils import FileUtils
from src.utils.image_utils import ImageUtils


def _bench(fn, iterations=1000):
    """Return median per-call time in microseconds."""
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        for _ in range(iterations):
            fn()
        times.append((time.perf_counter() - t0) / iterations * 1e6)
    times.sort()
    return times[len(times) // 2]


@pytest.mark.perf
def test_perf_easing_lookup_is_fast():
    """get_easing_function doit rester sous 50 µs / call (table dict)."""
    median_us = _bench(lambda: get_easing_function("Lineaire"))
    assert median_us < 50, f"Easing lookup trop lent: {median_us:.2f} µs"


@pytest.mark.perf
def test_perf_blend_mode_lookup_is_fast():
    median_us = _bench(lambda: get_blend_mode("Cross-dissolve"))
    assert median_us < 50, f"Blend lookup trop lent: {median_us:.2f} µs"


@pytest.mark.perf
def test_perf_pad_numbers_is_fast():
    median_us = _bench(lambda: FileUtils.pad_numbers_in_filename("photo_123_v45.jpg"))
    assert median_us < 200, f"pad_numbers trop lent: {median_us:.2f} µs"


@pytest.mark.perf
def test_perf_blend_images_100x100():
    img1 = np.zeros((100, 100, 3), dtype=np.uint8)
    img2 = np.full_like(img1, 200)
    median_us = _bench(lambda: ImageUtils.blend_images(img1, img2, 0.5), iterations=200)
    # cv2.addWeighted on 100x100 should be sub-ms
    assert median_us < 5000, f"blend_images trop lent: {median_us:.2f} µs"


@pytest.mark.perf
def test_perf_resize_image_keep_aspect():
    img = np.zeros((1000, 1000, 3), dtype=np.uint8)
    median_us = _bench(lambda: ImageUtils.resize_image(img, (200, 200), keep_aspect=True), iterations=50)
    assert median_us < 50_000, f"resize 1000x1000->200x200 trop lent: {median_us:.2f} µs"


@pytest.mark.perf
def test_perf_face_morpher_compute_triangulation():
    """Triangulation Delaunay sur 76 points (68 landmarks + 8 boundary)."""
    from src.core.face_morpher import FaceMorpher

    morpher = FaceMorpher()
    landmarks = np.random.rand(76, 2).astype(np.float32) * 1000
    median_us = _bench(lambda: morpher.compute_triangulation(landmarks), iterations=20)
    # scipy.spatial.Delaunay on 76 points: should be < 5 ms
    assert median_us < 50_000, f"Triangulation trop lente: {median_us:.2f} µs"
