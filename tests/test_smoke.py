"""Smoke tests — workflows principaux executes sans crash.

Goal: filet de securite avant Phase E. Ces tests doivent rester verts apres
chaque modification de code metier (sauf changement intentionnel documente).
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


# ============= Module imports =============

def test_all_src_modules_import_without_crash():
    """All non-UI src modules import. UI mainloop excluded (would create CTk root).

    export_manager and validators were moved to _archive/ (commit 11) — they
    were never consumed by the running app despite being re-exported from
    src.utils.__init__.
    """
    import src.core.face_aligner  # noqa: F401
    import src.core.face_detector  # noqa: F401
    import src.core.face_morpher  # noqa: F401
    import src.core.video_encoder  # noqa: F401
    import src.modules.step_align  # noqa: F401
    import src.modules.step_export  # noqa: F401
    import src.modules.step_import  # noqa: F401
    import src.modules.step_morph  # noqa: F401
    import src.modules.workflow_manager  # noqa: F401
    import src.ui.widgets  # noqa: F401
    import src.utils.config_manager  # noqa: F401
    import src.utils.file_utils  # noqa: F401
    import src.utils.image_utils  # noqa: F401
    import src.utils.logger  # noqa: F401
    import src.utils.paths  # noqa: F401
    import src.utils.splash_screen  # noqa: F401


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


# ============= Logger =============

def test_logger_basic_levels_log_without_crash(tmp_path):
    logger = Logger("TestLogger", log_dir=str(tmp_path), file_output=False)
    logger.info("info msg")
    logger.warning("warn msg")
    logger.error("err msg")
    logger.success("ok msg")
    logger.debug("debug msg")
    history = logger.get_history()
    # debug filtered by default INFO level, so 4 entries minimum
    assert len(history) >= 4


def test_logger_callback_receives_entries(tmp_path):
    logger = Logger("TestCallback", log_dir=str(tmp_path), file_output=False)
    received = []
    logger.add_callback(received.append)
    logger.info("hello")
    assert len(received) == 1
    assert received[0].message == "hello"


# ============= WorkflowManager =============

def test_workflow_manager_step_lifecycle():
    mgr = WorkflowManager()
    step = WorkflowStep(id="x", name="X", description="d",
                       function=lambda c, p, l: {})
    mgr.add_step(step)
    assert len(mgr.steps) == 1
    mgr.enable_step("x", False)
    assert mgr.get_step("x").enabled is False


def test_workflow_manager_runs_simple_step(tmp_path):
    mgr = WorkflowManager()
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    invoked = []

    def fake_step(ctx, progress, logger):
        invoked.append("yes")
        return {"ok": True}

    step = WorkflowStep(id="s", name="S", description="d", function=fake_step)
    mgr.add_step(step)
    mgr._context.run_dir = str(runs_dir)  # bypass create_run_directory
    # Stub create_run_directory to avoid creating ./runs in repo
    mgr.create_run_directory = lambda: str(runs_dir)
    mgr.run()
    assert invoked == ["yes"]


# ============= FileUtils =============

def test_file_utils_get_image_files_lists_only_images(temp_image_dir):
    (temp_image_dir / "ignore.txt").write_text("hello")
    files = FileUtils.get_image_files(str(temp_image_dir))
    assert len(files) == 3
    assert all(f.endswith(".png") for f in files)


def test_file_utils_pad_numbers_in_filename():
    assert FileUtils.pad_numbers_in_filename("image_1.jpg") == "image_000001.jpg"
    # multiple numeric tokens get padded independently
    assert FileUtils.pad_numbers_in_filename("photo_99_v2.png") == "photo_000099_v000002.png"


# ============= ImageUtils =============

def test_image_utils_load_image_returns_none_on_missing():
    assert ImageUtils.load_image("/nonexistent/path.png") is None


def test_image_utils_save_load_roundtrip(tmp_path, synthetic_image):
    path = str(tmp_path / "out.png")
    assert ImageUtils.save_image(synthetic_image, path) is True
    loaded = ImageUtils.load_image(path)
    assert loaded is not None
    assert loaded.shape == synthetic_image.shape


# ============= validate_image_file =============

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
