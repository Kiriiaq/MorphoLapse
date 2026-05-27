"""Functional tests for VideoEncoder state machine + preset honoring."""

from src.core.video_encoder import VideoEncoder


def test_video_encoder_initial_state():
    enc = VideoEncoder()
    assert enc._frames_dir is None
    assert enc.frame_count == 0
    assert enc._preset == "medium"
    assert enc._crf == 23
    assert enc.is_encoding is False


def test_video_encoder_preset_slow_maps_to_crf_20(tmp_path):
    enc = VideoEncoder()
    enc._ffmpeg_available = True  # bypass ffmpeg presence check
    enc.start_encoding(str(tmp_path / "out.mp4"), fps=25, size=(100, 100), quality="slow")
    assert enc._preset == "slow"
    assert enc._crf == 20
    assert enc.is_encoding is True


def test_video_encoder_preset_ultrafast_maps_to_crf_28(tmp_path):
    enc = VideoEncoder()
    enc._ffmpeg_available = True
    enc.start_encoding(str(tmp_path / "out.mp4"), fps=25, size=(100, 100), quality="ultrafast")
    assert enc._preset == "ultrafast"
    assert enc._crf == 28


def test_video_encoder_unknown_preset_falls_back(tmp_path):
    enc = VideoEncoder()
    enc._ffmpeg_available = True
    enc.start_encoding(str(tmp_path / "out.mp4"), fps=25, size=(100, 100), quality="garbage")
    assert enc._preset == "medium"
    assert enc._crf == 23


def test_video_encoder_finish_without_start_returns_false():
    enc = VideoEncoder()
    enc._ffmpeg_available = True
    # never call start_encoding
    assert enc.finish_encoding() is False


def test_video_encoder_write_frame_without_start_logs_error(tmp_path, synthetic_image):
    enc = VideoEncoder()
    enc._ffmpeg_available = True
    # Doesn't crash, just logs
    enc.write_frame(synthetic_image)
    assert enc.frame_count == 0  # nothing written


def test_video_encoder_write_frame_resizes_to_target(tmp_path, synthetic_image):
    enc = VideoEncoder()
    enc._ffmpeg_available = True
    enc.start_encoding(str(tmp_path / "out.mp4"), fps=25, size=(50, 50))
    enc.write_frame(synthetic_image)  # synthetic is 100x100; encoder resizes to 50x50
    assert enc.frame_count == 1
    # Le dossier des frames est désormais nommé « frames » (visible) au lieu
    # de « _frames_temp » (caché) — cf. start_encoding(frames_subdir=...).
    written = list((tmp_path / "frames").iterdir())
    assert len(written) == 1
    # Verify the frame file is non-empty
    assert written[0].stat().st_size > 0


def test_video_encoder_write_pause_frames(tmp_path, synthetic_image):
    enc = VideoEncoder()
    enc._ffmpeg_available = True
    enc.start_encoding(str(tmp_path / "out.mp4"), fps=25, size=(100, 100))
    enc.write_pause_frames(synthetic_image, count=5)
    assert enc.frame_count == 5
