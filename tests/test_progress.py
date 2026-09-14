"""Progress reflects selected points, failed attempts and actual saved output."""
from pathlib import Path

import pytest

from nanomech.progress import AnalysisProgress
from nanomech.requests import VeaRequest
from nanomech.workflows import run_vea


@pytest.fixture
def vea_request(tmp_path, monkeypatch):
    from nanomech import calibration

    root = Path(__file__).resolve().parents[1] / "test-data-large"
    sample = root / "VEA-500-5k-sample.nhf"
    calibration_path = root / "VEA-500-5k-calibration.nhf"
    if not sample.exists() or not calibration_path.exists():
        pytest.skip("Local VEA files unavailable")
    monkeypatch.setattr(calibration, "SCRIPT_DIRECTORY", tmp_path)
    # Nonzero map indices ensure progress counts attempts rather than indices.
    return VeaRequest(sample, calibration_path, output=tmp_path / "output",
                      max_count=2, crop_area="0,1:1,1")


@pytest.mark.parametrize("fail_static", [False, True])
def test_progress_includes_failed_and_skipped_points(vea_request, monkeypatch, fail_static):
    if fail_static:
        def fail(*args, **kwargs):
            raise ValueError("Forced failure")
        monkeypatch.setattr("nanomech.static.fit_static_point", fail)
    events = []

    def observe(event):
        events.append(event)
        if event.stage == "complete":
            assert list(vea_request.output.glob("*/run.json")), "Complete must follow saving"

    result = run_vea(vea_request, progress_callback=observe)
    assert result.status == ("failed" if fail_static else "success")
    stages = list(dict.fromkeys(e.stage for e in events))
    assert stages == ["selection", "calibration", "output_preparation", "static", "save_static",
                      "dynamic", "save_dynamic", "moduli", "save_results", "complete"]
    for stage in ("static", "dynamic", "moduli"):
        updates = [e for e in events if e.stage == stage]
        assert [(e.completed, e.total) for e in updates] == [(0, 2), (1, 2), (2, 2)]
        assert [e.percent for e in updates] == [0, 50, 100]
    assert events[-1] == AnalysisProgress("complete", 2, 2)
    assert all(e.percent is None for e in events if e.stage.startswith("save_"))


def test_dry_run_reports_only_calibration(vea_request):
    from dataclasses import replace

    events = []
    result = run_vea(replace(vea_request, dry_run=True), progress_callback=events.append)
    assert events == [AnalysisProgress("selection"), AnalysisProgress("calibration", 0, 1),
                      AnalysisProgress("calibration", 1, 1), AnalysisProgress("dry_run_complete", 1, 1)]
    assert result.output_dir is None and not vea_request.output.exists()


def test_fatal_error_does_not_report_completion(vea_request):
    from dataclasses import replace

    events = []
    with pytest.raises((ValueError, OSError)):
        run_vea(replace(vea_request, calibration=vea_request.output / "missing.nhf"),
                progress_callback=events.append)
    assert events[-1] == AnalysisProgress("calibration", 0, 1)
    assert not vea_request.output.exists()
