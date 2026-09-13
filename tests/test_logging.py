"""CLI logging level and standalone configuration checks."""
import logging
from pathlib import Path
import subprocess
import sys
import json
import pytest

from nanomech.cli import main
from nanomech.selection import select_points


@pytest.fixture(autouse=True)
def restore_root_level(monkeypatch):
    monkeypatch.setattr("nanomech.vea_command.load_calibration", lambda path: None)
    monkeypatch.setattr("nanomech.vea_command.prepare_calibration", lambda *a, **k: None)
    level = logging.getLogger().level
    yield
    logging.getLogger().setLevel(level)


@pytest.mark.parametrize("before,after", [(["--log-level", "debug"], []),
                                        ([], ["--log_level", "DEBUG"])])
@pytest.mark.parametrize("options,expected", [([], "crop_area=ALL, max_count=ALL"),
    (["--crop_area", "0,0:1,1", "--max_count", "3"], "crop_area=0,0:1,1, max_count=3")])
def test_debug_selection(before, after, options, expected, monkeypatch, caplog):
    monkeypatch.setattr("nanomech.vea_command.select_sample_points",
                        lambda *args, **kwargs: select_points(2, 2, **kwargs))
    with caplog.at_level(logging.DEBUG):
        assert main(before + ["vea", "--sample", "unused.nhf", "--dry-run"] + after + options) == 0
    records = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert any(expected in r.getMessage() for r in records)


def test_debug_effective_config(tmp_path, monkeypatch, caplog):
    config = tmp_path / "vea.json"
    config.write_text(json.dumps({"schema_version": 1, "command": "vea", "sample": "unused.nhf",
                                 "crop_area": "0,0:1,1", "max_count": 4}))
    monkeypatch.setattr("nanomech.vea_command.select_sample_points",
                        lambda *args, **kwargs: select_points(2, 2, **kwargs))
    with caplog.at_level(logging.DEBUG):
        assert main(["vea", "--config", str(config), "--max_count", "2", "--dry-run", "--log-level", "DEBUG"]) == 0
    assert "crop_area=0,0:1,1, max_count=2" in caplog.text


@pytest.mark.parametrize("level", ["INFO", "WARNING", "ERROR", "CRITICAL"])
def test_level_filters_debug(level, monkeypatch, caplog):
    monkeypatch.setattr("nanomech.vea_command.select_sample_points",
                        lambda *args, **kwargs: select_points(2, 2, **kwargs))
    with caplog.at_level(logging.DEBUG):
        assert main(["vea", "--sample", "unused.nhf", "--dry-run", "--log-level", level]) == 0
    assert not any(r.levelno == logging.DEBUG for r in caplog.records)
    assert bool(caplog.records) == (level == "INFO")


def test_cli_failure_is_info(tmp_path, caplog, capsys):
    with caplog.at_level(logging.INFO, logger="nanomech.cli"):
        assert main(["excitation-fit", "--input", str(tmp_path / "missing.nhf")]) == 1
    records = [r for r in caplog.records if r.name == "nanomech.cli"]
    assert len(records) == 1
    assert records[0].levelno == logging.INFO
    assert "missing.nhf" in records[0].getMessage()
    assert capsys.readouterr().out == ""


def test_standalone_logging_once():
    code = (
        "import logging; from nanomech.logging_config import configure_logging; "
        "configure_logging(); configure_logging(); "
        "logging.getLogger('nanomech.test').info('visible-message'); "
        "logging.getLogger('nanomech.test').debug('hidden-message')"
    )
    result = subprocess.run([sys.executable, "-c", code],
                            cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, check=True)
    assert result.stdout == ""
    assert result.stderr.count("visible-message") == 1
    assert "INFO [nanomech.test]" in result.stderr
    assert "hidden-message" not in result.stderr
