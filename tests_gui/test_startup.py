"""Check Windows COM startup ordering in an isolated Python process."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="Windows OLE initialization")
def test_qt_initializes_ole_before_nanosurf():
    pytest.importorskip("PySide6")
    code = '''
import ctypes
import sys
from PySide6 import QtWidgets
from PySide6.QtCore import QTimer
from nanomech_gui.main_window import MainWindow
assert "nanosurf" not in sys.modules

ole32 = ctypes.WinDLL("ole32")
ole32.OleInitialize.argtypes = [ctypes.c_void_p]
ole32.OleInitialize.restype = ctypes.c_long
OriginalApplication = QtWidgets.QApplication

class CheckedApplication(OriginalApplication):
    def __init__(self, argv):
        assert "nanosurf" not in sys.modules
        # Exercise the Windows platform plugin's STA requirement while using
        # offscreen rendering so this test never opens a desktop window.
        assert ole32.OleInitialize(None) in (0, 1)
        super().__init__(argv)
        QTimer.singleShot(0, self.quit)

QtWidgets.QApplication = CheckedApplication
from nanomech_gui.app import main
try:
    assert main([]) == 0
    assert "nanosurf" in sys.modules
    assert ole32.OleInitialize(None) in (0, 1)
    ole32.OleUninitialize()
finally:
    ole32.OleUninitialize()
'''
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OleInitialize() failed" not in result.stderr
