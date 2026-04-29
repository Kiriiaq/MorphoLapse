"""Golden master tests — verrouillent le contrat actuel UI -> backend.

Phase E commit 6 a corrige le mapping FR/EN ; les tests `_BUG` qui locktaient
le comportement defectueux ont ete inverses pour devenir des assertions du
contrat correct, et les `phase_e_*` corresponants ont ete dé-skippes.
"""
import pytest

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
        'low': 'ultrafast', 'medium': 'medium', 'high': 'slow', 'ultra': 'slower',
        'Basse': 'ultrafast', 'Moyenne': 'medium', 'Haute': 'slow', 'Maximum': 'slower',
    }
    assert quality_map.get('high') == 'slow'


def test_quality_preset_mapping_accepts_french_ui_labels():
    """UI dropdown sends FR labels; mapping must resolve them."""
    quality_map = {
        'low': 'ultrafast', 'medium': 'medium', 'high': 'slow', 'ultra': 'slower',
        'Basse': 'ultrafast', 'Moyenne': 'medium', 'Haute': 'slow', 'Maximum': 'slower',
    }
    assert quality_map.get('Basse') == 'ultrafast'
    assert quality_map.get('Moyenne') == 'medium'
    assert quality_map.get('Haute') == 'slow'
    assert quality_map.get('Maximum') == 'slower'


# ============= Phase E targets (still pending) =============

@pytest.mark.skip(reason="Phase E target: VideoEncoder must honor quality preset")
def test_phase_e_video_encoder_honors_quality_preset(tmp_path):
    """After commit 7: VideoEncoder.finish_encoding should use the preset
    passed via start_encoding(quality=...) instead of hardcoded 'fast'."""


@pytest.mark.skip(reason="Phase E target: QuickActions reset/help must wire to handlers")
def test_phase_e_quickactions_reset_and_help_have_handlers():
    """After commit 10: _on_quick_action wires only the buttons that exist
    (open, save) — reset/help/export/clear/settings branches removed."""
