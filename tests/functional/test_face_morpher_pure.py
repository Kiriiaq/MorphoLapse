"""Functional tests for FaceMorpher's testable parts (no dlib needed)."""

import numpy as np
import pytest

from src.core.face_morpher import BlendMode, EasingFunction, FaceMorpher, MorphConfig


@pytest.fixture
def morpher():
    return FaceMorpher()


# ============= Easing functions =============


@pytest.mark.parametrize(
    "easing,t_input,expected_range",
    [
        (EasingFunction.LINEAR, 0.5, (0.5, 0.5)),
        (EasingFunction.EASE_IN, 0.5, (0.25, 0.25)),
        (EasingFunction.EASE_OUT, 0.5, (0.75, 0.75)),
        (EasingFunction.CUBIC, 0.5, (0.125, 0.125)),
        (EasingFunction.EASE_IN_OUT, 0.0, (0.0, 0.0)),
        (EasingFunction.EASE_IN_OUT, 1.0, (1.0, 1.0)),
    ],
)
def test_easing_known_values(morpher, easing, t_input, expected_range):
    result = morpher._apply_easing(t_input, easing)
    assert expected_range[0] - 1e-9 <= result <= expected_range[1] + 1e-9


def test_easing_endpoints_are_0_and_1(morpher):
    """All easings must map t=0 -> 0 and t=1 -> 1."""
    for easing in EasingFunction:
        assert morpher._apply_easing(0.0, easing) == pytest.approx(0.0, abs=1e-6)
        assert morpher._apply_easing(1.0, easing) == pytest.approx(1.0, abs=1e-6)


def test_easing_bounce_stays_in_unit_interval(morpher):
    """Bounce values are bounded in [0, 1] for t in [0, 1]."""
    for t in np.linspace(0, 1, 30):
        v = morpher._apply_easing(float(t), EasingFunction.BOUNCE)
        assert 0.0 <= v <= 1.0 + 1e-6


def test_easing_unknown_returns_t_unchanged(morpher):
    """Defensive default: unknown enum (impossible normally) returns t."""

    class FakeEasing:
        pass

    assert morpher._apply_easing(0.7, FakeEasing()) == 0.7


# ============= Blend modes =============


def test_blend_alpha_at_0_returns_image1(morpher, synthetic_image):
    """`_blend_images` consumes normalized [0,1] floats and returns uint8 [0,255]."""
    a = synthetic_image.astype(np.float32) / 255.0
    b = np.full_like(synthetic_image, 200, dtype=np.float32) / 255.0
    out = morpher._blend_images(a, b, 0.0, BlendMode.ALPHA)
    assert np.allclose(out, synthetic_image, atol=1)


def test_blend_alpha_at_1_returns_image2(morpher, synthetic_image):
    a = synthetic_image.astype(np.float32) / 255.0
    b_uint = np.full_like(synthetic_image, 200)
    b = b_uint.astype(np.float32) / 255.0
    out = morpher._blend_images(a, b, 1.0, BlendMode.ALPHA)
    assert np.allclose(out, b_uint, atol=1)


def test_blend_additive_clips_at_255(morpher):
    """Normalized 1.0 + 1.0 must clip to 1.0 -> 255."""
    a = np.ones((10, 10, 3), dtype=np.float32)
    b = np.ones((10, 10, 3), dtype=np.float32)
    out = morpher._blend_images(a, b, 0.5, BlendMode.ADDITIVE)
    assert (out == 255).all()


def test_blend_multiply_darker_than_either_input(morpher):
    """Multiply of normalized 0.5 + 0.5 yields ≤ 0.5 -> ≤ 128."""
    a = np.full((10, 10, 3), 0.5, dtype=np.float32)
    b = np.full((10, 10, 3), 0.5, dtype=np.float32)
    out = morpher._blend_images(a, b, 0.5, BlendMode.MULTIPLY)
    assert (out <= 128).all()


def test_blend_screen_returns_valid_uint8(morpher):
    """Screen mode always returns uint8 in [0, 255], never NaN nor wrap."""
    a = np.full((10, 10, 3), 0.3, dtype=np.float32)
    b = np.full((10, 10, 3), 0.6, dtype=np.float32)
    out = morpher._blend_images(a, b, 0.5, BlendMode.SCREEN)
    assert out.dtype == np.uint8
    assert out.min() >= 0 and out.max() <= 255
    # Pour ces inputs, le résultat est entre les deux entrées (sous-additif)
    assert 76 <= out.mean() <= 153  # entre 0.3*255 et 0.6*255


# ============= Triangulation =============


def test_compute_triangulation_returns_array_of_3_indices(morpher):
    landmarks = np.random.rand(76, 2).astype(np.float32) * 100
    tri = morpher.compute_triangulation(landmarks)
    assert tri.shape[1] == 3  # each triangle = 3 indices
    assert tri.dtype.kind in "iu"  # integer indices
    assert tri.max() < 76


def test_compute_triangulation_handles_minimum_3_points(morpher):
    """3 points = 1 triangle."""
    landmarks = np.array([[0, 0], [10, 0], [5, 10]], dtype=np.float32)
    tri = morpher.compute_triangulation(landmarks)
    assert len(tri) == 1


# ============= Cross-dissolve =============


def test_cross_dissolve_yields_correct_frame_count(morpher, synthetic_image):
    other = np.full_like(synthetic_image, 200)
    frames = list(morpher.stream_cross_dissolve(synthetic_image, other, num_frames=10))
    assert len(frames) == 10


def test_cross_dissolve_first_frame_close_to_image1(morpher, synthetic_image):
    other = np.full_like(synthetic_image, 200)
    frames = list(morpher.stream_cross_dissolve(synthetic_image, other, num_frames=5))
    # first frame should be (mostly) image1
    assert np.mean(np.abs(frames[0].astype(int) - synthetic_image.astype(int))) < 30


def test_cross_dissolve_last_frame_close_to_image2(morpher, synthetic_image):
    other = np.full_like(synthetic_image, 200)
    frames = list(morpher.stream_cross_dissolve(synthetic_image, other, num_frames=5))
    assert np.mean(np.abs(frames[-1].astype(int) - other.astype(int))) < 30


# ============= MorphConfig =============


def test_morph_config_defaults():
    cfg = MorphConfig()
    assert cfg.easing == EasingFunction.LINEAR
    assert cfg.blend_mode == BlendMode.ALPHA


def test_morph_config_quality_settings_keys(morpher):
    assert set(morpher._quality_settings.keys()) == {"low", "medium", "high", "ultra"}
