"""Switch display languages without changing settings, results or progress."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


def test_language_switch_preserves_analysis_state():
    pytest.importorskip("PySide6")
    code = '''
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QGroupBox
app = QApplication([])
from nanomech_gui.main_window import MainWindow
from nanomech.progress import AnalysisProgress

w = MainWindow()
assert w.translator.language == "ja"
assert w.load_config("examples/vea.toml")
t, e = w.vea_tab, w.excitation_fit_tab
t.shape.setCurrentIndex(t.shape.findData("cone"))
t.model.setCurrentText("DMT_Cone")
before = t.build_request()
path_label = t.sample_label.text()
t.update_progress(AnalysisProgress("dynamic", 3, 8))
e.source = Path("measurements.nhf")
e.path_label.setText(str(e.source))
for degree in range(6):
    e.table.item(degree, 1).setText(str(degree + 0.1234))
coefficients = [e.table.item(i, 1).text() for i in range(6)]

w.language_combo.setCurrentIndex(w.language_combo.findData("en"))
assert w.load_config_button.text() == "Load analysis settings"
assert "Probe" in [group.title() for group in t.findChildren(QGroupBox)]
assert t.fit_button.text() == "Start fitting"
assert t.sensitivity.placeholderText() == "Blank: use NHF metadata"
assert t.shape.currentText() == "Cone" and t.shape.currentData() == "cone"
assert t.model.currentText() == "DMT_Cone" and t.build_request() == before
assert t.sample_label.text() == path_label
assert "Dynamic analysis" in t.progress_label.text() and "3 / 8" in t.progress_label.text()
assert "37.5%" in t.progress_label.text() and t.progress.value() == 375
assert w.config_label.text().startswith("Loaded:")
assert e.table.horizontalHeaderItem(0).text() == "Degree"
assert e.table.horizontalHeaderItem(1).text() == "Coefficient"
assert e.table.item(5, 0).text() == "5 (c5)"
assert [e.table.item(i, 1).text() for i in range(6)] == coefficients
assert e.path_label.text() == "measurements.nhf"

with patch("nanomech_gui.main_window.QFileDialog.getOpenFileName", return_value=("", "")) as dialog:
    w.select_config()
    assert dialog.call_args.args[1] == "Load analysis settings"
with patch("nanomech_gui.excitation_fit_tab.QFileDialog.getOpenFileName", return_value=("", "")) as dialog:
    e.select_file()
    assert dialog.call_args.args[1] == "Select NHF file"

t.max_count.setText("not-a-number")
t.start_analysis()
assert "Enter an integer for Maximum points." in t.status_label.text()
assert not t.is_busy
w.language_combo.setCurrentIndex(w.language_combo.findData("ja"))
assert "最大解析数には整数" in t.status_label.text()
assert t.shape.currentText() == "円錐" and t.model.currentText() == "DMT_Cone"
assert e.table.horizontalHeaderItem(1).text() == "係数"
assert [e.table.item(i, 1).text() for i in range(6)] == coefficients
t.max_count.setText(str(before.max_count))
assert t.build_request() == before

# Retained progress is translated even while a worker owns the tab.
t.worker = object()
t.update_progress(AnalysisProgress("static", 1, 2))
w.language_combo.setCurrentIndex(w.language_combo.findData("en"))
assert t.is_busy and "Static analysis" in t.progress_label.text()
assert "50.0%" in t.progress_label.text() and t.build_request() == before
t.worker = None

# Config application in English still uses language-independent model identifiers.
assert w.load_config("examples/vea.toml")
assert t.shape.currentText() == "Sphere" and t.model.currentText() == "Hertz"
assert t.status_label.text() == "Settings loaded."
assert not w.load_config("missing-config.toml")
assert w.config_label.text().startswith("Could not load settings:")
w.close()
'''
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
