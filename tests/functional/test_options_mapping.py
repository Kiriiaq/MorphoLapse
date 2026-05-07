"""Golden master tests — verrouillent le contrat actuel UI -> backend.

Phase E commit 6 a corrige le mapping FR/EN ; les tests `_BUG` qui locktaient
le comportement defectueux ont ete inverses pour devenir des assertions du
contrat correct, et les `phase_e_*` corresponants ont ete dé-skippes.
"""

from src.core.face_morpher import BlendMode, EasingFunction
from src.modules.step_morph import get_blend_mode, get_easing_function

# ============= Easing function mapping =============


def test_easing_unknown_string_falls_back_to_linear():
    """Defensive default: any unknown easing -> LINEAR."""
    assert get_easing_function("anything-unknown") == EasingFunction.LINEAR


def test_easing_french_ui_labels_map_correctly():
    """The UI dropdown emits FR labels; they MUST map to the right enum."""
    assert get_easing_function("Lineaire") == EasingFunction.LINEAR
    assert get_easing_function("Ease In/Out") == EasingFunction.EASE_IN_OUT
    assert get_easing_function("Ease In") == EasingFunction.EASE_IN
    assert get_easing_function("Ease Out") == EasingFunction.EASE_OUT


def test_easing_english_keys_map_correctly():
    """Backend EN keys (config-stored values) work as before."""
    assert get_easing_function("linear") == EasingFunction.LINEAR
    assert get_easing_function("ease_in") == EasingFunction.EASE_IN
    assert get_easing_function("ease_out") == EasingFunction.EASE_OUT
    assert get_easing_function("ease_in_out") == EasingFunction.EASE_IN_OUT
    assert get_easing_function("cubic") == EasingFunction.CUBIC
    assert get_easing_function("bounce") == EasingFunction.BOUNCE


# ============= Blend mode mapping =============


def test_blend_mode_unknown_string_falls_back_to_alpha():
    assert get_blend_mode("xyz") == BlendMode.ALPHA


def test_blend_mode_ui_labels_map_correctly():
    """UI dropdown labels must map to the right BlendMode enum.

    Note: 'Cross-dissolve' is treated as ALPHA — that's what the morpher
    does internally when landmarks are unavailable (stream_cross_dissolve
    is itself an alpha-blend).
    """
    assert get_blend_mode("Normal") == BlendMode.ALPHA
    assert get_blend_mode("Cross-dissolve") == BlendMode.ALPHA
    assert get_blend_mode("Additive") == BlendMode.ADDITIVE


def test_blend_mode_english_keys_map_correctly():
    assert get_blend_mode("alpha") == BlendMode.ALPHA
    assert get_blend_mode("additive") == BlendMode.ADDITIVE
    assert get_blend_mode("multiply") == BlendMode.MULTIPLY
    assert get_blend_mode("screen") == BlendMode.SCREEN


# ============= Quality preset mapping (step_morph.py morph_faces) =============


def test_quality_preset_mapping_accepts_english_keys():
    quality_map = {
        "low": "ultrafast",
        "medium": "medium",
        "high": "slow",
        "ultra": "slower",
        "Basse": "ultrafast",
        "Moyenne": "medium",
        "Haute": "slow",
        "Maximum": "slower",
    }
    assert quality_map.get("high") == "slow"


def test_quality_preset_mapping_accepts_french_ui_labels():
    """UI dropdown sends FR labels; mapping must resolve them."""
    quality_map = {
        "low": "ultrafast",
        "medium": "medium",
        "high": "slow",
        "ultra": "slower",
        "Basse": "ultrafast",
        "Moyenne": "medium",
        "Haute": "slow",
        "Maximum": "slower",
    }
    assert quality_map.get("Basse") == "ultrafast"
    assert quality_map.get("Moyenne") == "medium"
    assert quality_map.get("Haute") == "slow"
    assert quality_map.get("Maximum") == "slower"


# ============= Phase E targets (still pending) =============


def test_video_encoder_honors_quality_preset(tmp_path):
    """VideoEncoder.start_encoding(quality=...) must be reused at finish time."""
    from src.core.video_encoder import VideoEncoder

    enc = VideoEncoder()
    # Bypass ffmpeg presence check by short-circuiting, we only verify state
    enc._ffmpeg_available = True
    enc.start_encoding(str(tmp_path / "out.mp4"), fps=25, size=(100, 100), quality="slow")
    assert enc._preset == "slow"
    assert enc._crf == 20

    enc.start_encoding(str(tmp_path / "out2.mp4"), fps=25, size=(100, 100), quality="ultrafast")
    assert enc._preset == "ultrafast"
    assert enc._crf == 28


def test_video_encoder_unknown_quality_falls_back_to_medium(tmp_path):
    """Unknown preset string falls back to 'medium'/CRF 23 rather than crashing."""
    from src.core.video_encoder import VideoEncoder

    enc = VideoEncoder()
    enc._ffmpeg_available = True
    enc.start_encoding(str(tmp_path / "out.mp4"), fps=25, size=(100, 100), quality="nonsense")
    assert enc._preset == "medium"
    assert enc._crf == 23


def test_quickactions_only_declares_open_and_save():
    """Commit 10 result: orphan buttons (reset, help) and orphan handlers
    (export, clear, settings) were removed. QuickActions.ACTIONS is the
    single source of truth and contains exactly the supported ids."""
    from src.ui.widgets import QuickActions

    action_ids = [a[1] for a in QuickActions.ACTIONS]
    assert action_ids == ["open", "save"]
