"""Main window containing one tab per analysis command."""
from pathlib import Path

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QComboBox, QFileDialog, QHBoxLayout, QLabel, QMainWindow, QPushButton, QTabWidget, QVBoxLayout, QWidget

from .i18n import Message, Translator
from .excitation_fit_tab import ExcitationFitTab
from .vea_tab import VeaTab, text_label


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nanomech")
        self.resize(1000, 720)

        self.translator = Translator(self)
        self.tabs = QTabWidget(self)
        self.vea_tab = VeaTab(translator=self.translator)
        self.excitation_fit_tab = ExcitationFitTab(translator=self.translator)
        self.tabs.addTab(self.vea_tab, "VEA")
        self.tabs.addTab(self.excitation_fit_tab, "excitation-fit")
        self.config_path = None
        self.load_config_button = QPushButton("解析設定の読み込み")
        self.load_config_button.clicked.connect(self.select_config)
        self.config_label = text_label("設定ファイルを読み込むと、対応するタブの解析条件を更新します。")
        header = QHBoxLayout()
        header.addWidget(self.load_config_button)
        header.addWidget(self.config_label, 1)
        header.addWidget(QLabel("Language / 言語"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("日本語", "ja")
        self.language_combo.addItem("English", "en")
        self.language_combo.currentIndexChanged.connect(
            lambda index: self.translator.set_language(self.language_combo.currentData())
        )
        header.addWidget(self.language_combo)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addLayout(header)
        layout.addWidget(self.tabs)
        self.setCentralWidget(container)
        self.translator.bind_tree(self)
        self.vea_tab.busy_changed.connect(self.update_config_button)
        self.excitation_fit_tab.busy_changed.connect(self.update_config_button)

    @Slot()
    def update_config_button(self):
        self.load_config_button.setEnabled(not any(
            tab.is_busy for tab in (self.vea_tab, self.excitation_fit_tab)
        ))

    @Slot()
    def select_config(self):
        if any(tab.is_busy for tab in (self.vea_tab, self.excitation_fit_tab)):
            return
        filename, _ = QFileDialog.getOpenFileName(
            self, self.translator.text("解析設定を読み込む"), str(self.config_path.parent) if self.config_path else "",
            self.translator.text("解析設定 (*.toml *.json);;TOML (*.toml);;JSON (*.json)"),
        )
        if filename:
            self.load_config(Path(filename))

    def load_config(self, path):
        if any(tab.is_busy for tab in (self.vea_tab, self.excitation_fit_tab)):
            return False
        try:
            from nanomech.config import load_settings

            path = Path(path).resolve()
            command, settings = load_settings(path)
            tab = self.vea_tab if command == "vea" else self.excitation_fit_tab
            tab.apply_settings(settings, path)
        except (ValueError, OSError, TypeError, OverflowError) as error:
            self.config_label.set_message("設定を読み込めませんでした: {error}", error=error)
            return False
        self.config_path = path
        self.tabs.setCurrentWidget(tab)
        note = Message("\nDry-Run設定です。Dry-Runボタンで実行してください。") if command == "vea" and settings.get("dry_run") else ""
        self.config_label.set_message("読み込み済み: {path}{note}", path=path, note=note)
        self.config_label.setToolTip(str(path))
        return True

    def closeEvent(self, event):
        for tab in (self.vea_tab, self.excitation_fit_tab):
            if tab.is_busy:
                tab.status_label.setText(
                    "解析中です。完了後にウィンドウを閉じてください。"
                )
                event.ignore()
                return
        super().closeEvent(event)
