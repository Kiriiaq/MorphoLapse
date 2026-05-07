"""Functional tests for ConfigManager, Logger, FileUtils, ImageUtils, validate_image_file.

Anciens `tests/test_smoke.py` reclassés en functional, plus quelques cas
nominaux + négatifs additionnels.
"""

import pytest
from src.modules.step_import import ImageValidationError, validate_image_file
from src.modules.workflow_manager import (
    WorkflowManager,
    WorkflowStep,
)
from src.utils.config_manager import ConfigManager
from src.utils.file_utils import FileUtils
from src.utils.image_utils import ImageUtils
from src.utils.logger import Logger


# ============= ConfigManager =============


def test_config_manager_set_get_roundtrip(temp_config_path):
    cm = ConfigManager(config_path=temp_config_path)
    cm.set("morphing.fps", 42, auto_save=True)
    cm.set("video.format", "mp4", auto_save=True)

    cm2 = ConfigManager(config_path=temp_config_path)
    cm2.load()
    assert cm2.get("morphing.fps") == 42
    assert cm2.get("video.format") == "mp4"


def test_config_manager_reset_to_defaults(temp_config_path):
    cm = ConfigManager(config_path=temp_config_path)
    cm.set("morphing.fps", 999, auto_save=False)
    cm.reset_to_defaults()
    assert cm.get("morphing.fps") == 25


def test_config_manager_get_unknown_key_returns_default(temp_config_path):
    cm = ConfigManager(config_path=temp_config_path)
    assert cm.get("nonexistent.key", "fallback") == "fallback"


def test_config_manager_change_callback_fires(temp_config_path):
    cm = ConfigManager(config_path=temp_config_path)
    received = []
    cm.add_change_callback(lambda cfg: received.append(cfg.morphing.fps))
    cm.set("morphing.fps", 30, auto_save=False)
    assert received == [30]


def test_config_manager_change_callback_remove(temp_config_path):
    cm = ConfigManager(config_path=temp_config_path)
    received = []
    cb = lambda cfg: received.append(1)  # noqa: E731
    cm.add_change_callback(cb)
    cm.remove_change_callback(cb)
    cm.set("morphing.fps", 30, auto_save=False)
    assert received == []


# ============= Logger =============


def test_logger_basic_levels_log_without_crash(tmp_path):
    logger = Logger("TestLogger", log_dir=str(tmp_path), file_output=False)
    logger.info("info msg")
    logger.warning("warn msg")
    logger.error("err msg")
    logger.success("ok msg")
    logger.debug("debug msg")
    history = logger.get_history()
    assert len(history) >= 4


def test_logger_callback_receives_entries(tmp_path):
    logger = Logger("TestCallback", log_dir=str(tmp_path), file_output=False)
    received = []
    logger.add_callback(received.append)
    logger.info("hello")
    assert len(received) == 1
    assert received[0].message == "hello"


def test_logger_callback_exception_does_not_recurse(tmp_path):
    """Un callback qui throw ne doit ni récurser ni faire crasher Logger._log."""
    logger = Logger("TestRecurse", log_dir=str(tmp_path), file_output=False)

    def bad_callback(entry):
        raise RuntimeError("intentional")

    logger.add_callback(bad_callback)
    # Si récursion infinie, ce log ferait stack overflow
    logger.info("trigger")
    assert len(logger.get_history()) >= 1


def test_logger_history_filtered_by_level(tmp_path):
    from src.utils.logger import LogLevel

    logger = Logger("TestFilter", log_dir=str(tmp_path), file_output=False)
    logger.info("a")
    logger.warning("b")
    logger.error("c")
    only_warn_plus = logger.get_history(level=LogLevel.WARNING)
    assert len(only_warn_plus) == 2  # b, c


# ============= WorkflowManager =============


def test_workflow_manager_step_lifecycle():
    mgr = WorkflowManager()
    step = WorkflowStep(id="x", name="X", description="d", function=lambda c, p, _l: {})
    mgr.add_step(step)
    assert len(mgr.steps) == 1
    mgr.enable_step("x", False)
    assert mgr.get_step("x").enabled is False


def test_workflow_manager_runs_simple_step(tmp_path):
    mgr = WorkflowManager()
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    invoked = []

    def fake_step(ctx, progress, _l):
        invoked.append("yes")
        return {"ok": True}

    step = WorkflowStep(id="s", name="S", description="d", function=fake_step)
    mgr.add_step(step)
    mgr._context.run_dir = str(runs_dir)
    mgr.create_run_directory = lambda: str(runs_dir)
    mgr.run()
    assert invoked == ["yes"]


def test_workflow_manager_remove_step():
    mgr = WorkflowManager()
    step = WorkflowStep(id="z", name="Z", description="d", function=lambda c, p, _l: {})
    mgr.add_step(step)
    assert mgr.get_step("z") is not None
    mgr.remove_step("z")
    assert mgr.get_step("z") is None


def test_workflow_manager_set_context():
    mgr = WorkflowManager()
    mgr.set_context(input_dir="/tmp/x", reference_image="/tmp/r.jpg")
    assert mgr._context.input_dir == "/tmp/x"
    assert mgr._context.reference_image == "/tmp/r.jpg"


# ============= FileUtils =============


def test_file_utils_get_image_files_lists_only_images(temp_image_dir):
    (temp_image_dir / "ignore.txt").write_text("hello")
    files = FileUtils.get_image_files(str(temp_image_dir))
    assert len(files) == 3
    assert all(f.endswith(".png") for f in files)


def test_file_utils_get_image_files_invalid_dir():
    """Returns empty list (not crash) for non-existent dir."""
    assert FileUtils.get_image_files("/nonexistent/path/to/dir") == []


def test_file_utils_pad_numbers_in_filename():
    assert FileUtils.pad_numbers_in_filename("image_1.jpg") == "image_000001.jpg"
    assert FileUtils.pad_numbers_in_filename("photo_99_v2.png") == "photo_000099_v000002.png"


def test_file_utils_pad_numbers_no_digits():
    assert FileUtils.pad_numbers_in_filename("plain_name.jpg") == "plain_name.jpg"


def test_file_utils_get_file_info(tmp_path, synthetic_image):
    import cv2

    p = tmp_path / "x.png"
    cv2.imwrite(str(p), synthetic_image)
    info = FileUtils.get_file_info(str(p))
    assert info["name"] == "x.png"
    assert info["extension"] == ".png"
    assert info["size"] > 0
    assert info["width"] == 100
    assert info["height"] == 100


def test_file_utils_human_readable_size():
    assert FileUtils._human_readable_size(500) == "500.0 B"
    assert FileUtils._human_readable_size(1500).endswith("KB")
    assert FileUtils._human_readable_size(1500 * 1024).endswith("MB")


def test_file_utils_ensure_unique_filename(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("a")
    unique = FileUtils.ensure_unique_filename(str(p))
    assert unique != str(p)
    assert "_1" in unique


def test_file_utils_create_run_directory(tmp_path):
    run = FileUtils.create_run_directory(str(tmp_path))
    assert "01_import" in str(list(__import__("os").listdir(run)))


# ============= ImageUtils =============


def test_image_utils_load_image_returns_none_on_missing():
    assert ImageUtils.load_image("/nonexistent/path.png") is None


def test_image_utils_save_load_roundtrip(tmp_path, synthetic_image):
    path = str(tmp_path / "out.png")
    assert ImageUtils.save_image(synthetic_image, path) is True
    loaded = ImageUtils.load_image(path)
    assert loaded is not None
    assert loaded.shape == synthetic_image.shape


def test_image_utils_resize_keeps_aspect(synthetic_image):
    resized = ImageUtils.resize_image(synthetic_image, (200, 50), keep_aspect=True)
    assert resized.shape[:2] == (50, 200)  # height, width


def test_image_utils_resize_no_aspect(synthetic_image):
    resized = ImageUtils.resize_image(synthetic_image, (50, 200), keep_aspect=False)
    assert resized.shape[:2] == (200, 50)


def test_image_utils_blend_returns_average(synthetic_image):
    import numpy as np

    other = np.full_like(synthetic_image, 200)
    blended = ImageUtils.blend_images(synthetic_image, other, 0.5)
    assert blended.shape == synthetic_image.shape
    assert blended.dtype == synthetic_image.dtype


def test_image_utils_add_border(synthetic_image):
    bordered = ImageUtils.add_border(synthetic_image, size=10)
    assert bordered.shape[0] == synthetic_image.shape[0] + 20
    assert bordered.shape[1] == synthetic_image.shape[1] + 20


def test_image_utils_create_thumbnail_square(synthetic_image):
    thumb = ImageUtils.create_thumbnail(synthetic_image, size=64)
    assert thumb.shape[0] == thumb.shape[1] == 64


# ============= validate_image_file (positive + negative) =============


def test_validate_image_file_accepts_valid_png(tmp_path, synthetic_image):
    import cv2

    p = tmp_path / "valid.png"
    cv2.imwrite(str(p), synthetic_image)
    is_valid, _err, _warns = validate_image_file(str(p))
    assert is_valid is True


def test_validate_image_file_rejects_missing_file(tmp_path):
    with pytest.raises(ImageValidationError) as exc:
        validate_image_file(str(tmp_path / "missing.png"))
    assert exc.value.error_type == "NOT_FOUND"


def test_validate_image_file_rejects_too_small(tmp_path):
    p = tmp_path / "tiny.png"
    p.write_bytes(b"x")
    with pytest.raises(ImageValidationError) as exc:
        validate_image_file(str(p))
    assert exc.value.error_type == "TOO_SMALL"


def test_validate_image_file_rejects_corrupted_png(tmp_path):
    """File with .png extension but garbage bytes."""
    p = tmp_path / "fake.png"
    p.write_bytes(b"X" * 200)  # > MIN_IMAGE_SIZE but no PNG signature
    with pytest.raises(ImageValidationError) as exc:
        validate_image_file(str(p))
    assert exc.value.error_type == "CORRUPTED"


def test_validate_image_file_message_attribute_set(tmp_path):
    """Regression test: ImageValidationError must store .message (Phase 2 fix)."""
    p = tmp_path / "tiny.png"
    p.write_bytes(b"x")
    try:
        validate_image_file(str(p))
    except ImageValidationError as e:
        assert hasattr(e, "message")
        assert "too small" in e.message.lower()


def test_validate_image_file_warns_on_unusual_extension(tmp_path, synthetic_image):
    """Unusual extension produces a warning, not a hard reject."""
    import cv2

    p = tmp_path / "image.weird"
    cv2.imwrite(str(tmp_path / "tmp.png"), synthetic_image)
    # Copy bytes
    p.write_bytes((tmp_path / "tmp.png").read_bytes())
    is_valid, _err, warnings = validate_image_file(str(p))
    assert is_valid is True
    assert any("extension" in w.lower() for w in warnings)
