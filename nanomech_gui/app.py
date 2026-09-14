"""Qt application entry point, independent of the CLI entry point."""
import sys


def main(argv=None):
    from PySide6.QtWidgets import QApplication
    # Qt must initialize Windows OLE (STA) before nanosurf imports pythoncom
    # with its MTA default. Importing the window also loads analysis modules.
    app = QApplication(sys.argv if argv is None else ["nanomech-gui", *argv])
    app.setApplicationName("Nanomech")
    from .main_window import MainWindow

    window = MainWindow()
    window.show()
    return app.exec()
