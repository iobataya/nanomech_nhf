"""NHF selection and excitation coefficient fitting."""
from pathlib import Path

from .i18n import LocalizedLabel, Translator

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)


class ExcitationFitWorker(QThread):
    """Keep NHF reading and fitting off the GUI thread."""

    def __init__(self, source, parent=None):
        super().__init__(parent)
        self.source = source
        self.result = None
        self.error = None

    def run(self):
        try:
            from nanomech.workflows import excitation_fit

            self.result, _ = excitation_fit(self.source)
        except Exception as error:
            self.error = str(error) or type(error).__name__


class ExcitationFitTab(QWidget):
    busy_changed = Signal()

    def __init__(self, parent=None, translator=None):
        super().__init__(parent)
        self.translator = translator or Translator(self)
        self.source = None
        self.worker = None

        self.select_button = QPushButton("NHFファイルを選択")
        self.select_button.clicked.connect(self.select_file)
        self.path_label = LocalizedLabel("ファイルが選択されていません")
        self.path_label.setTextFormat(Qt.TextFormat.PlainText)
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.table = QTableWidget(6, 2)
        self.table.setHorizontalHeaderLabels(["次数", "係数"])
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        for degree in range(6):
            self.table.setItem(degree, 0, QTableWidgetItem(f"{degree}次 (c{degree})"))
            self.table.setItem(degree, 1, QTableWidgetItem("—"))

        self.fit_button = QPushButton("フィッティングを開始")
        self.fit_button.setEnabled(False)
        self.fit_button.clicked.connect(self.start_fit)
        self.status_label = LocalizedLabel("")
        self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.status_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.select_button)
        layout.addWidget(self.path_label)
        layout.addWidget(self.table)
        layout.addWidget(self.fit_button)
        layout.addWidget(self.status_label)
        self.translator.bind_tree(self)
        self.translator.changed.connect(self.retranslate_table)
        self.retranslate_table()

    def retranslate_table(self):
        self.table.setHorizontalHeaderLabels([self.translator.text("次数"), self.translator.text("係数")])
        for degree in range(6):
            self.table.item(degree, 0).setText(self.translator.text("{degree}次 (c{degree})", degree=degree))

    @property
    def is_busy(self):
        # Keep controls locked until the finished handler has consumed the result.
        return self.worker is not None

    def clear_coefficients(self):
        for degree in range(6):
            self.table.item(degree, 1).setText("—")

    def apply_settings(self, settings, path):
        self.source = settings.get("input")
        self.config_path = path
        self.path_label.setText(str(self.source) if self.source else "ファイルが選択されていません")
        self.path_label.setToolTip(str(self.source) if self.source else "")
        self.clear_coefficients()
        self.status_label.setText("設定を読み込みました。フィッティングを開始できます。" if self.source else "NHFファイルを選択してください。")
        self.fit_button.setEnabled(self.source is not None)

    @Slot()
    def select_file(self):
        if self.is_busy:
            return
        filename, _ = QFileDialog.getOpenFileName(
            self, self.translator.text("NHFファイルを選択"), str(self.source.parent) if self.source else "",
            self.translator.text("NHFファイル (*.nhf *.NHF)"),
        )
        if not filename:
            return
        self.source = Path(filename)
        self.path_label.setText(str(self.source))
        self.path_label.setToolTip(str(self.source))
        self.clear_coefficients()
        self.status_label.clear()
        self.fit_button.setEnabled(True)

    @Slot()
    def start_fit(self):
        if self.source is None or self.is_busy:
            return
        self.clear_coefficients()
        self.status_label.setText("フィッティング中…")
        self.select_button.setEnabled(False)
        self.fit_button.setEnabled(False)
        self.worker = ExcitationFitWorker(self.source, self)
        self.busy_changed.emit()
        self.worker.finished.connect(self.finish_fit)
        self.worker.start()

    @Slot()
    def finish_fit(self):
        worker = self.worker
        if worker.error is not None:
            self.status_label.set_message("フィッティングに失敗しました: {error}", error=worker.error)
        else:
            for degree, coefficient in enumerate(worker.result.coefficients):
                self.table.item(degree, 1).setText(format(coefficient, ".16g"))
            self.status_label.setText("フィッティングが完了しました。")
        self.worker = None
        self.busy_changed.emit()
        worker.deleteLater()
        self.select_button.setEnabled(True)
        self.fit_button.setEnabled(True)
