"""Verify queued progress updates are displayed while the worker is running."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("fail", [False, True])
def test_live_progress_and_failure(fail):
    pytest.importorskip("PySide6")
    code = '''
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop, QTimer

app = QApplication([])
from nanomech_gui.vea_tab import VeaTab
from nanomech.progress import AnalysisProgress
from nanomech.selection import PointSelection

tab = VeaTab()
tab.show()
tab.sample = Path("unused.nhf")
received = Event()
snapshots = []
should_fail = sys.argv[1] == "True"

def run(request, *, progress_callback):
    progress_callback(AnalysisProgress("static", 1, 4))
    if not received.wait(5):
        raise RuntimeError("GUI did not receive progress while worker was active")
    if should_fail:
        raise ValueError("simulated failure")
    progress_callback(AnalysisProgress("save_results"))
    progress_callback(AnalysisProgress("complete", 4, 4))
    return SimpleNamespace(status="success", selection=PointSelection(2, 2, (0,1,2,3)), output_dir=None)

def observe(event):
    snapshots.append((event.stage, tab.progress_label.text(), tab.progress.value(), tab.progress.maximum()))
    if event.stage == "static":
        received.set()

with patch("nanomech.workflows.run_vea", run):
    loop = QEventLoop()
    tab.start_analysis()
    tab.worker.progress_changed.connect(observe)
    tab.worker.finished.connect(loop.quit)
    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    timeout.start(10000)
    loop.exec()
    assert not tab.is_busy, "Worker timed out"

stage, label, value, maximum = snapshots[0]
assert stage == "static" and "静的解析" in label and "1 / 4 点" in label and "25.0%" in label
assert (value, maximum) == (250, 1000)
assert tab.fit_button.isEnabled() and tab.dry_run_button.isEnabled()
if should_fail:
    assert "simulated failure" in tab.status_label.text()
    assert tab.progress.isHidden() and "25.0%" in tab.progress_label.text()
else:
    assert snapshots[1][0] == "save_results" and snapshots[1][3] == 0
    assert "進捗率: —" in snapshots[1][1]
    assert "4 / 4 点" in tab.progress_label.text() and "100.0%" in tab.progress_label.text()
    assert not tab.progress.isHidden()
tab.close()
'''
    result = subprocess.run(
        [sys.executable, "-c", code, str(fail)],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
