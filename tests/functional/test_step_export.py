"""Functional tests for step_export.export_results."""

import json
from pathlib import Path

from src.modules.step_export import export_results
from src.modules.workflow_manager import WorkflowContext


def test_step_export_writes_summary_and_metadata(tmp_path):
    """Even without aligned_images / output_video, summary + metadata files are written."""
    context = WorkflowContext(
        run_dir=str(tmp_path / "run"),
        input_dir=str(tmp_path / "in"),
        output_dir="",
        images=["a.jpg", "b.jpg"],
        config={"fps": 25, "transition_duration": 3.0},
    )
    Path(context.run_dir).mkdir()

    progress_calls = []
    result = export_results(context, lambda c, t, m: progress_calls.append((c, t, m)))

    export_dir = Path(result["export_dir"])
    assert export_dir.exists()
    assert (export_dir / "run_summary.json").exists()
    assert (export_dir / "metadata.txt").exists()
    assert len(progress_calls) >= 4

    # Summary has the keys we expect
    summary = json.loads((export_dir / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["input"]["image_count"] == 2

    # Metadata contains the version (centralized in src.__version__)
    metadata_text = (export_dir / "metadata.txt").read_text(encoding="utf-8")
    assert "MORPHOLAPSE" in metadata_text
    assert "version" in metadata_text


def test_step_export_copies_video_when_present(tmp_path):
    context = WorkflowContext(run_dir=str(tmp_path / "r"), input_dir="", output_dir="", images=[], config={})
    Path(context.run_dir).mkdir()
    fake_video = tmp_path / "morph.mp4"
    fake_video.write_bytes(b"fake mp4 bytes" * 100)
    context.output_video = str(fake_video)

    result = export_results(context, lambda *a: None)
    copied = next(p for p in Path(result["export_dir"]).iterdir() if p.suffix == ".mp4")
    assert copied.read_bytes() == fake_video.read_bytes()


def test_step_export_uses_centralized_version(tmp_path):
    """Regression: metadata.version must come from src.__version__, not be hardcoded."""
    from src import __version__

    context = WorkflowContext(run_dir=str(tmp_path / "r"), input_dir="", output_dir="", images=[], config={})
    Path(context.run_dir).mkdir()
    result = export_results(context, lambda *a: None)
    metadata = (Path(result["export_dir"]) / "metadata.txt").read_text(encoding="utf-8")
    assert __version__ in metadata
