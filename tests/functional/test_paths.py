"""Functional tests for src.utils.paths resource resolution."""

from pathlib import Path

from src.utils import paths


def test_get_resource_root_in_source_mode():
    root = paths.get_resource_root()
    assert isinstance(root, Path)
    # In source mode root is the project dir, which contains pyproject.toml
    assert (root / "pyproject.toml").exists()


def test_get_icon_path_points_under_assets():
    p = paths.get_icon_path()
    assert p.parts[-2:] == ("icons", "icone.ico")
    assert "assets" in p.parts


def test_get_dlib_model_path_points_under_assets():
    p = paths.get_dlib_model_path()
    assert p.name == "shape_predictor_68_face_landmarks.dat"
    assert "assets" in p.parts


def test_resource_root_frozen_uses_meipass(monkeypatch, tmp_path):
    """When sys.frozen + sys._MEIPASS are set (PyInstaller bundle),
    paths must resolve under _MEIPASS, not the source tree."""
    import sys

    fake_meipass = tmp_path / "_MEI"
    fake_meipass.mkdir()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(fake_meipass), raising=False)
    assert paths.get_resource_root() == fake_meipass
