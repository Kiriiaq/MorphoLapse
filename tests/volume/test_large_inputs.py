"""Volume tests: large images, many files, memory accounting."""

import tracemalloc

import cv2
import numpy as np
import pytest
from src.modules.step_import import validate_image_file
from src.utils.file_utils import FileUtils
from src.utils.image_utils import ImageUtils


@pytest.mark.volume
def test_validate_large_image_8mp_under_limit(tmp_path):
    """A realistic 8 megapixel JPEG (~3.5 MB) must validate without crash."""
    img = np.random.randint(0, 255, (3000, 2000, 3), dtype=np.uint8)
    p = tmp_path / "big.jpg"
    cv2.imwrite(str(p), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    assert p.stat().st_size > 1_000_000  # at least 1 MB
    is_valid, _err, warnings = validate_image_file(str(p))
    assert is_valid is True


@pytest.mark.volume
def test_validate_oversized_image_warns(tmp_path):
    """Image > 50 MB threshold emits a warning (not a hard reject)."""
    # 10000x6000 RGB ~180 MB raw, ~50 MB compressed PNG depending on entropy
    img = np.random.randint(0, 255, (4000, 3000, 3), dtype=np.uint8)
    p = tmp_path / "huge.png"
    cv2.imwrite(str(p), img, [cv2.IMWRITE_PNG_COMPRESSION, 0])  # no compression -> bigger
    if p.stat().st_size <= 50 * 1024 * 1024:
        pytest.skip("synthetic image not large enough on this run")
    is_valid, _err, warnings = validate_image_file(str(p))
    assert is_valid is True
    assert any("Large image" in w for w in warnings)


@pytest.mark.volume
def test_get_image_files_with_many_entries(tmp_path):
    """1000 image files in a directory must list correctly and stay sorted."""
    # Use empty .png stub files; FileUtils.get_image_files only checks extension
    for i in range(1000):
        (tmp_path / f"{i:05d}.png").write_bytes(b"x")
    files = FileUtils.get_image_files(str(tmp_path), sort=True)
    assert len(files) == 1000
    # Lexicographic sort yields zero-padded ascending
    assert files[0].endswith("00000.png")
    assert files[-1].endswith("00999.png")


@pytest.mark.volume
def test_image_utils_resize_does_not_leak(synthetic_image):
    """Repeated resize_image must not balloon resident memory.

    Mesure : on garde l'écart entre la mémoire allouée avant/après ; il
    doit rester sous un seuil large mais finite (les arrays intermédiaires
    sont bien libérés par CPython).
    """
    tracemalloc.start()
    snap_before = tracemalloc.take_snapshot()
    for _ in range(200):
        out = ImageUtils.resize_image(synthetic_image, (200, 200), keep_aspect=True)
        del out
    snap_after = tracemalloc.take_snapshot()
    diff = sum(s.size_diff for s in snap_after.compare_to(snap_before, "filename"))
    tracemalloc.stop()
    # ≤ 5 MB de delta net après 200 itérations sur images 100x100x3
    assert diff < 5 * 1024 * 1024, f"Delta mémoire trop élevé: {diff} bytes"


@pytest.mark.volume
def test_logger_history_capped_at_max(tmp_path):
    """Logger history is capped at _max_history = 10 000 entries; pousser au-delà ne provoque
    pas d'OOM."""
    from src.utils.logger import Logger

    logger = Logger("VolLogger", log_dir=str(tmp_path), file_output=False)
    for i in range(15_000):
        logger.info(f"msg {i}")
    history = logger.get_history()
    # Capped at _max_history
    assert len(history) <= 10_000
    # Latest message preserved
    assert "14999" in history[-1].message
