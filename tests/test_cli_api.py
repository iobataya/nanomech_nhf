"""Exercise the shared API through its CLI adapter, without GUI tests."""
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("option", ["--max-count", "--max-plot-sample"])
def test_invalid_conditions_fail_before_io(option, monkeypatch, caplog):
    from nanomech.cli import main

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid conditions must fail before reading the sample")

    monkeypatch.setattr("nanomech.workflows.select_sample_points", forbidden)
    assert main(["vea", "--sample", "unused.nhf", option, "-1"]) == 1
    assert option[2:].replace("-", "_") in caplog.text


def test_cli_analysis_without_gui_imports(tmp_path):
    code = '''
import importlib.abc
import sys
from pathlib import Path

class NoGui(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"PySide6", "PyQt6", "PySide2", "PyQt5", "nanomech_gui"}:
            raise AssertionError("CLI imported GUI dependency: " + fullname)

sys.meta_path.insert(0, NoGui())
from nanomech.cli import main
from nanomech import calibration
calibration.SCRIPT_DIRECTORY = Path(sys.argv[1])
assert main(["vea", "--sample", "tests/data/VEA-CleanDrive-500-5k-80uW-single.nhf",
             "--calibration", "tests/data/VEA-CleanDrive-500-5k-80uW-single.nhf",
             "--output", sys.argv[1], "--max-count", "1",
             "--dry-run", "--plot-calibration"]) == 0
assert list(Path(sys.argv[1]).glob("*/calibration/*.png"))
'''
    completed = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path)],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
