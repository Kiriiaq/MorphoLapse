"""Smoke — every src module imports without crash.

Pure import test : aucune logique métier ne tourne, on vérifie juste qu'il
n'y a pas d'erreur d'import (typos, deps manquantes, circulaires).
"""


def test_all_src_modules_import_without_crash():
    """All non-UI src modules import. UI mainloop excluded (creates CTk root).

    export_manager / validators are in _archive/ — confirmed orphan during audit.
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


def test_main_entry_point_imports():
    """main.py top-level imports work (deps probe is in main(), not at module load)."""
    import importlib.util
    import sys
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("morpholapse_main", Path(__file__).parent.parent.parent / "main.py")
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["morpholapse_main"] = module
    spec.loader.exec_module(module)
    # If we got here, import didn't crash (CHECK_DEPS not called at module level)
    assert hasattr(module, "main")
    assert callable(module.main)
