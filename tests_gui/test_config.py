"""Configuration loading updates the form atomically without starting analysis."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


def test_load_settings_into_tabs(tmp_path):
    pytest.importorskip("PySide6")
    (tmp_path / "config.toml").write_text('''schema_version=1
command="vea"
[cli]
sample="sample.nhf"
calibration="calibration.nhf"
output="out"
max_points=7
crop_area="1,2:3,4"
plot_sample=true
plot_calibration=true
max_plot_sample=2
excitation="CleanDrive"
correct_drag=false
dry_run=true
[probe]
sensitivity=1e-7
spring_constant=0.08
tip_radius=1.23456789e-8
cone_half_angle=17.123456
poisson_ratio=0.4123456
[static]
model="dmt_cone"
fit_direction="retract"
baseline_start=0.123456
baseline_end=0.654321
''', encoding="utf-8")
    (tmp_path / "minimal.toml").write_text('schema_version=1\ncommand="vea"\n', encoding="utf-8")
    (tmp_path / "bad.toml").write_text('schema_version=1\ncommand="vea"\n[static]\nbaseline_start=0.8\nbaseline_end=0.2\n', encoding="utf-8")
    (tmp_path / "unknown.toml").write_text('schema_version=1\ncommand="vea"\nunknown=2\n', encoding="utf-8")
    (tmp_path / "excitation.toml").write_text('schema_version=1\ncommand="excitation-fit"\n[cli]\ninput="excitation.nhf"\n', encoding="utf-8")
    (tmp_path / "legacy.json").write_text('{"schema_version":1,"command":"vea","sample":"relative.nhf","max_count":3}', encoding="utf-8")
    code = '''
from pathlib import Path
from unittest.mock import patch
import math
import sys
from PySide6.QtWidgets import QApplication
app = QApplication([])
from nanomech_gui.main_window import MainWindow
w = MainWindow()
w.show()
app.processEvents()
root = Path(sys.argv[1])
t = w.vea_tab
assert w.load_config_button.parent() is not t
assert w.load_config_button.mapTo(w.centralWidget(), w.load_config_button.rect().topLeft()).y() < w.tabs.y()
with patch("nanomech_gui.main_window.QFileDialog.getOpenFileName", return_value=(str(root / "config.toml"), "")):
    w.load_config_button.click()
assert w.config_path == root / "config.toml"
assert w.tabs.currentWidget() is t and not t.is_busy
r = t.build_request(True)
assert r.sample == root / "sample.nhf" and r.calibration == root / "calibration.nhf"
assert r.output == root / "out" and r.max_count == 7 and r.crop_area == "1,2:3,4"
assert r.plot_sample and r.plot_calibration and r.max_plot_sample == 2
assert r.excitation == "CleanDrive" and not r.correct_drag
assert t.shape.currentText() == "円錐" and t.model.currentText() == "DMT_Cone"
assert r.static.fit_direction == "Retract"
assert math.isclose(r.static.tip_radius, 1.23456789e-8, rel_tol=1e-14)
assert r.static.cone_half_angle == 17.123456 and r.static.poisson_ratio == 0.4123456
assert r.static.baseline_start == 0.123456 and r.static.baseline_end == 0.654321
assert r.probe_config.sensitivity == 1e-7 and r.probe.sensitivity is None
assert float(t.sensitivity.text()) == 100 and r.config_path == root / "config.toml"
assert "Dry-Run" in w.config_label.text()
t.sensitivity.setText("120")
r = t.build_request()
assert math.isclose(r.probe.sensitivity, 120e-9) and r.probe_config.sensitivity is None
assert r.probe_source == "GUI"
before = t.build_request()
for name in ("bad.toml", "unknown.toml", "missing.toml"):
    assert not w.load_config(root / name)
    assert t.build_request() == before
    assert w.config_path == root / "config.toml"
with patch("nanomech_gui.main_window.QFileDialog.getOpenFileName", return_value=("", "")):
    w.load_config_button.click()
assert t.build_request() == before
t.worker = object()
t.busy_changed.emit()
assert not w.load_config_button.isEnabled()
assert not w.load_config(root / "minimal.toml")
t.worker = None
t.busy_changed.emit()
assert w.load_config_button.isEnabled()
assert w.load_config(root / "minimal.toml")
assert t.sample is None and t.calibration is None and not t.fit_button.isEnabled()
assert t.model.currentText() == "Hertz" and t.shape.currentText() == "球"
assert not t.plot_sample.isChecked() and t.max_count.text() == "" and t.sensitivity.text() == ""
assert t.baseline_start.value() == 0.05
assert w.load_config(root / "legacy.json")
assert t.sample == Path("relative.nhf") and t.build_request().max_count == 3
assert w.load_config(root / "excitation.toml")
assert w.tabs.currentWidget() is w.excitation_fit_tab
assert w.excitation_fit_tab.source == root / "excitation.nhf"
assert w.excitation_fit_tab.fit_button.isEnabled() and not w.excitation_fit_tab.is_busy
assert all(w.excitation_fit_tab.table.item(i,1).text() == "—" for i in range(6))
w.close()
'''
    result = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path)],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
