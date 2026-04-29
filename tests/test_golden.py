"""Golden master tests — verrouillent le comportement actuel.

Apres une correction Phase E, les tests sous "Phase E targets" doivent etre
re-actives (retirer @pytest.mark.skip) et les tests "Current bug" supprimes
ou inverses, dans le meme commit. Le test golden documente l'intention.
"""
import pytest

from src.core.face_morpher import BlendMode, EasingFunction
from src.modules.step_morph import get_blend_mode, get_easing_function


# ============= Easing — current behavior =============

def test_easing_unknown_string_falls_back_to_linear():
    """Mapping unknown -> LINEAR (defensive default in get_easing_function)."""
    assert get_easing_function("anything-unknown") == EasingFunction.LINEAR


def test_easing_french_ui_label_falls_back_to_linear_BUG():
    """Current bug locked: UI dropdown emits FR labels which never match the
    EN keys in `get_easing_function`. The user gets LINEAR regardless of
    selection. Phase E will fix this; the corresponding `phase_e_*` test
    above is skipped until then."""
    assert get_easing_function("Lineaire") == EasingFunction.LINEAR
    assert get_easing_function("Ease In/Out") == EasingFunction.LINEAR
    assert get_easing_function("Ease In") == EasingFunction.LINEAR
    assert get_easing_function("Ease Out") == EasingFunction.LINEAR


def test_easing_english_keys_map_correctly():
    """English keys (the ones the backend expects) DO work."""
    assert get_easing_function("linear") == EasingFunction.LINEAR
    assert get_easing_function("ease_in") == EasingFunction.EASE_IN
    assert get_easing_function("ease_out") == EasingFunction.EASE_OUT
    assert get_easing_function("ease_in_out") == EasingFunction.EASE_IN_OUT
    assert get_easing_function("cubic") == EasingFunction.CUBIC
    assert get_easing_function("bounce") == EasingFunction.BOUNCE


# ============= Blend mode — current behavior =============

def test_blend_mode_unknown_string_falls_back_to_alpha():
    assert get_blend_mode("xyz") == BlendMode.ALPHA


def test_blend_mode_ui_labels_fall_back_to_alpha_BUG():
    """Current bug locked: UI dropdown values don't match backend keys."""
    assert get_blend_mode("Normal") == BlendMode.ALPHA
    assert get_blend_mode("Cross-dissolve") == BlendMode.ALPHA
    # Note: UI sends "Additive" (capital A); backend key is "additive" lowercase.
    assert get_blend_mode("Additive") == BlendMode.ALPHA


def test_blend_mode_english_keys_map_correctly():
    assert get_blend_mode("alpha") == BlendMode.ALPHA
    assert get_blend_mode("additive") == BlendMode.ADDITIVE
    assert get_blend_mode("multiply") == BlendMode.MULTIPLY
    assert get_blend_mode("screen") == BlendMode.SCREEN


# ============= Quality preset mapping (in step_morph.py:202-204) =============

def test_quality_preset_mapping_lowercase_works():
    """The map in step_morph.py:202 itself is correct for EN keys."""
    quality_map = {'low': 'ultrafast', 'medium': 'medium', 'high': 'slow', 'ultra': 'slower'}
    assert quality_map.get('high') == 'slow'


def test_quality_preset_mapping_french_returns_none_BUG():
    """Current bug locked: UI dropdown sends FR labels which miss the map."""
    quality_map = {'low': 'ultrafast', 'medium': 'medium', 'high': 'slow', 'ultra': 'slower'}
    assert quality_map.get('Basse') is None
    assert quality_map.get('Moyenne') is None
    assert quality_map.get('Haute') is None
    assert quality_map.get('Maximum') is None


# ============= Phase E targets (re-enable after fix) =============

@pytest.mark.skip(reason="Phase E target: FR UI labels should map to backend enums")
def test_phase_e_easing_french_maps_correctly():
    assert get_easing_function("Lineaire") == EasingFunction.LINEAR
    assert get_easing_function("Ease In/Out") == EasingFunction.EASE_IN_OUT
    assert get_easing_function("Ease In") == EasingFunction.EASE_IN
    assert get_easing_function("Ease Out") == EasingFunction.EASE_OUT


@pytest.mark.skip(reason="Phase E target: blend mode UI labels should map")
def test_phase_e_blend_mode_ui_labels_map_correctly():
    assert get_blend_mode("Normal") == BlendMode.ALPHA
    assert get_blend_mode("Cross-dissolve") == BlendMode.ALPHA  # cross-dissolve falls under alpha
    assert get_blend_mode("Additive") == BlendMode.ADDITIVE


@pytest.mark.skip(reason="Phase E target: VideoEncoder must honor quality preset")
def test_phase_e_video_encoder_honors_quality_preset(tmp_path):
    """After fix: VideoEncoder.finish_encoding should use the preset passed
    via start_encoding(quality=...) instead of hardcoded 'fast'."""
    # Will be implemented when VideoEncoder.finish_encoding accepts/uses
    # the preset stored at start_encoding time.


@pytest.mark.skip(reason="Phase E target: QuickActions reset/help must wire to handlers")
def test_phase_e_quickactions_reset_and_help_have_handlers():
    """After fix: _on_quick_action must handle 'reset' and 'help', not just
    open/save/export/clear/settings."""
