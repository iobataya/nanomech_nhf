"""VEA conditions and asynchronous execution of the shared workflow."""
from pathlib import Path
from dataclasses import asdict
from decimal import Decimal
import re
from time import monotonic

from .i18n import LocalizedLabel, Message, Translator, UiError

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QProgressBar,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

class VeaWorker(QThread):
    progress_changed = Signal(object)

    def __init__(self, request, parent=None):
        super().__init__(parent)
        self.request = request
        self.result = None
        self.error = None
        self._last_stage = None
        self._last_notification = 0.0

    def report_progress(self, event):
        # Bound GUI updates for large maps while retaining stage boundaries.
        now = monotonic()
        if (event.stage != self._last_stage or event.completed == event.total
                or now - self._last_notification >= .1):
            self.progress_changed.emit(event)
            self._last_stage = event.stage
            self._last_notification = now

    def run(self):
        try:
            from nanomech.workflows import run_vea

            self.result = run_vea(self.request, progress_callback=self.report_progress)
        except Exception as error:
            self.error = str(error) or type(error).__name__


def text_label(text):
    label = LocalizedLabel(text)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


def decimal_input(value, minimum, maximum, decimals=4):
    widget = QDoubleSpinBox()
    widget.setDecimals(decimals)
    widget.setRange(minimum, maximum)
    widget.setValue(value)
    widget.setKeyboardTracking(False)
    return widget


class VeaTab(QWidget):
    busy_changed = Signal()

    SHAPE_MODELS = {
        "sphere": ("Hertz", "DMT_Sphere"),
        "cone": ("Sneddon", "DMT_Cone"),
        "pyramid": ("Pyramid",),
    }

    def __init__(self, parent=None, translator=None):
        super().__init__(parent)
        self.translator = translator or Translator(self)
        # Load nanosurf-dependent defaults only after QApplication exists.
        from nanomech.static import StaticConfig

        self.worker = None
        self.sample = None
        self.calibration = None
        self.output = Path("results").resolve()
        self.last_result = None
        self.config_path = None
        self._loaded_probe = {}
        defaults = StaticConfig()

        self.form = QWidget()
        grid = QGridLayout(self.form)
        files = QGroupBox("Files")
        file_layout = QGridLayout(files)
        self.calibration_button = QPushButton("Calibrationを選択")
        self.sample_button = QPushButton("Sampleを選択")
        self.output_button = QPushButton("保存先を選択")
        self.calibration_label = text_label("未選択（保存済み校正キャッシュを使用）")
        self.sample_label = text_label("未選択")
        self.output_label = text_label(str(self.output))
        self.calibration_button.clicked.connect(lambda: self.select_file("calibration"))
        self.sample_button.clicked.connect(lambda: self.select_file("sample"))
        self.output_button.clicked.connect(self.select_output)
        for row, (button, label) in enumerate((
            (self.calibration_button, self.calibration_label),
            (self.sample_button, self.sample_label),
            (self.output_button, self.output_label),
        )):
            file_layout.addWidget(button, row, 0)
            file_layout.addWidget(label, row, 1)
        file_layout.setColumnStretch(1, 1)
        grid.addWidget(files, 0, 0, 1, 2)

        ranges = QGroupBox("Analysis Range")
        range_layout = QFormLayout(ranges)
        self.max_count = QLineEdit()
        self.max_count.setPlaceholderText("空欄：全点")
        self.crop_area = QLineEdit()
        self.crop_area.setPlaceholderText("x_start,y_start:x_end,y_end（空欄：全域）")
        self.plot_calibration = QCheckBox("Calibration")
        self.plot_sample = QCheckBox("Sample")
        plots = QHBoxLayout()
        plots.addWidget(self.plot_calibration)
        plots.addWidget(self.plot_sample)
        self.max_plot_sample = QLineEdit()
        self.max_plot_sample.setPlaceholderText("空欄：全点、0：出力なし")
        self.max_plot_sample.setEnabled(False)
        self.plot_sample.toggled.connect(self.max_plot_sample.setEnabled)
        range_layout.addRow("最大解析数", self.max_count)
        range_layout.addRow("Cropエリア", self.crop_area)
        range_layout.addRow("プロット出力", plots)
        range_layout.addRow("最大Sampleプロット数", self.max_plot_sample)
        grid.addWidget(ranges, 1, 0)

        probe = QGroupBox("プローブ情報")
        probe_layout = QFormLayout(probe)
        self.sensitivity = QLineEdit()
        self.spring_constant = QLineEdit()
        for widget in (self.sensitivity, self.spring_constant):
            widget.setPlaceholderText("空欄：NHFから取得")
        self.shape = QComboBox()
        for key, label in (("sphere", "球"), ("cone", "円錐"), ("pyramid", "四角錐")):
            self.shape.addItem(label, key)
        self.tip_radius = decimal_input(defaults.tip_radius * 1e9, .0001, 1e9)
        self.cone_half_angle = decimal_input(defaults.cone_half_angle, .0001, 89.9999)
        probe_layout.addRow("Sensitivity (nm/V)", self.sensitivity)
        probe_layout.addRow("Spring constant (N/m)", self.spring_constant)
        probe_layout.addRow("先端形状", self.shape)
        probe_layout.addRow("先端半径 (nm)", self.tip_radius)
        probe_layout.addRow("先端半角 (°)", self.cone_half_angle)
        grid.addWidget(probe, 1, 1)

        static = QGroupBox("Static")
        static_layout = QFormLayout(static)
        self.fit_direction = QComboBox()
        self.fit_direction.addItems(["Advance", "Retract"])
        self.model = QComboBox()
        self.poisson_ratio = decimal_input(defaults.poisson_ratio, -.9999, .5)
        self.baseline_start = decimal_input(defaults.baseline_start, 0, 1)
        self.baseline_end = decimal_input(defaults.baseline_end, 0, 1)
        static_layout.addRow("フィッティングセグメント", self.fit_direction)
        static_layout.addRow("モデル", self.model)
        static_layout.addRow("ポアソン比", self.poisson_ratio)
        static_layout.addRow("ベースライン開始（比率）", self.baseline_start)
        static_layout.addRow("ベースライン終了（比率）", self.baseline_end)
        self.shape.currentIndexChanged.connect(self.update_shape)
        self.update_shape(self.shape.currentIndex())
        grid.addWidget(static, 2, 0)

        dynamic = QGroupBox("Dynamic")
        dynamic_layout = QFormLayout(dynamic)
        self.excitation = QComboBox()
        self.excitation.addItems(["auto", "Piezo", "CleanDrive"])
        self.correct_drag = QCheckBox("流体抵抗補正を適用（Piezo）")
        self.correct_drag.setChecked(True)
        self.excitation.currentTextChanged.connect(
            lambda method: self.correct_drag.setEnabled(method != "CleanDrive")
        )
        dynamic_layout.addRow("励振方式", self.excitation)
        dynamic_layout.addRow(self.correct_drag)
        dynamic_layout.addRow(text_label("周波数・スイープ条件はNHFファイルから取得します。"))
        grid.addWidget(dynamic, 2, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(3, 1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.form)
        self.fit_button = QPushButton("フィッティングを開始")
        self.dry_run_button = QPushButton("Dry-Run")
        self.fit_button.clicked.connect(lambda: self.start_analysis(False))
        self.dry_run_button.clicked.connect(lambda: self.start_analysis(True))
        self.fit_button.setEnabled(False)
        self.dry_run_button.setEnabled(False)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(self.dry_run_button)
        buttons.addWidget(self.fit_button)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        self.progress_label = text_label("")
        self.progress_label.hide()
        self.status_label = text_label("")
        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        layout.addLayout(buttons)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        self.translator.bind_tree(self)
        self.translator.changed.connect(self.retranslate_choices)
        self.retranslate_choices()

    def retranslate_choices(self):
        # Keep item data stable; changing language must not select another model.
        for index, source in enumerate(("球", "円錐", "四角錐")):
            self.shape.setItemText(index, self.translator.text(source))

    @property
    def is_busy(self):
        return self.worker is not None

    def apply_settings(self, settings, path):
        """Validate a complete replacement before changing any visible inputs."""
        from nanomech.requests import ProbeOverrides, VeaRequest
        from nanomech.static import StaticConfig

        static = StaticConfig(**{key: settings.get(key, value)
                                 for key, value in asdict(StaticConfig()).items()})
        candidate = VeaRequest(
            sample=settings.get("sample", Path(".")), calibration=settings.get("calibration"),
            output=settings.get("output", Path("results").resolve()), static=static,
            max_count=settings.get("max_count"), crop_area=settings.get("crop_area"),
            max_plot_sample=settings.get("max_plot_sample"),
            plot_sample=settings.get("plot_sample", False), plot_calibration=settings.get("plot_calibration", False),
            excitation=settings.get("excitation", "auto"), correct_drag=settings.get("correct_drag", True),
            probe_config=ProbeOverrides(settings.get("sensitivity"), settings.get("spring_constant")),
        )
        candidate.validate()
        crop = candidate.crop_area
        if crop is not None:
            match = re.fullmatch(r"\s*(\d+)\s*,\s*(\d+)\s*:\s*(\d+)\s*,\s*(\d+)\s*", crop)
            if not match:
                raise UiError("Cropエリアは x_start,y_start:x_end,y_end で指定してください。")
            x0, y0, x1, y1 = map(int, match.groups())
            if x0 > x1 or y0 > y1:
                raise UiError("Cropエリアの開始座標は終了座標以下にしてください。")
        import math
        numeric_fields = (
            (self.tip_radius, static.tip_radius * 1e9), (self.cone_half_angle, static.cone_half_angle),
            (self.poisson_ratio, static.poisson_ratio), (self.baseline_start, static.baseline_start),
            (self.baseline_end, static.baseline_end),
        )
        sensitivity = candidate.probe_config.sensitivity
        sensitivity_nm = None if sensitivity is None else sensitivity * 1e9
        if any(not math.isfinite(value) for _, value in numeric_fields) or (
                sensitivity_nm is not None and not math.isfinite(sensitivity_nm)):
            raise UiError("設定値をGUIの表示単位に変換できません。")

        self.sample = settings.get("sample")
        self.calibration = candidate.calibration
        self.output = candidate.output
        self.config_path = path
        self.sample_label.setText(str(self.sample) if self.sample else "未選択")
        self.calibration_label.setText(str(self.calibration) if self.calibration else "未選択（保存済み校正キャッシュを使用）")
        self.output_label.setText(str(self.output))
        for widget, value in ((self.max_count, candidate.max_count), (self.crop_area, crop),
                              (self.max_plot_sample, candidate.max_plot_sample)):
            widget.setText("" if value is None else str(value))
        self.plot_sample.setChecked(candidate.plot_sample)
        self.plot_calibration.setChecked(candidate.plot_calibration)
        self._loaded_probe = {}
        for name, value, display in (
            ("sensitivity", sensitivity, sensitivity_nm),
            ("spring_constant", candidate.probe_config.spring_constant, candidate.probe_config.spring_constant),
        ):
            text = "" if display is None else format(display, ".17g")
            getattr(self, name).setText(text)
            if value is not None:
                self._loaded_probe[name] = (text, value)
        shape = next(shape for shape, models in self.SHAPE_MODELS.items() if static.model in models)
        self.shape.setCurrentIndex(self.shape.findData(shape))
        self.model.setCurrentText(static.model)
        for widget, value in numeric_fields:
            # Preserve file precision instead of silently rounding/clamping it.
            decimals = max(4, -Decimal(str(value)).as_tuple().exponent)
            widget.setDecimals(decimals)
            widget.setRange(min(widget.minimum(), value), max(widget.maximum(), value))
            widget.setValue(value)
        self.fit_direction.setCurrentText(static.fit_direction)
        self.excitation.setCurrentText(candidate.excitation)
        self.correct_drag.setChecked(candidate.correct_drag)
        self.last_result = None
        self.progress.hide()
        self.progress_label.hide()
        self.status_label.setText("設定を読み込みました。" if self.sample else "Sampleファイルを選択してください。")
        self.fit_button.setEnabled(self.sample is not None)
        self.dry_run_button.setEnabled(self.sample is not None)

    @Slot(int)
    def update_shape(self, index):
        shape = self.shape.currentData()
        self.model.clear()
        self.model.addItems(self.SHAPE_MODELS[shape])
        self.tip_radius.setEnabled(shape == "sphere")
        self.cone_half_angle.setEnabled(shape != "sphere")

    def select_file(self, kind):
        if self.is_busy:
            return
        current = getattr(self, kind)
        filename, _ = QFileDialog.getOpenFileName(
            self, self.translator.text("{kind} NHFを選択", kind=kind.capitalize()), str(current.parent) if current else "",
            self.translator.text("NHFファイル (*.nhf *.NHF)"),
        )
        if filename:
            setattr(self, kind, Path(filename))
            getattr(self, f"{kind}_label").setText(filename)
            self.status_label.clear()
            self.last_result = None
            self.progress.hide()
            self.progress_label.hide()
            self.fit_button.setEnabled(self.sample is not None)
            self.dry_run_button.setEnabled(self.sample is not None)

    @Slot()
    def select_output(self):
        if self.is_busy:
            return
        directory = QFileDialog.getExistingDirectory(self, self.translator.text("保存先を選択"), str(self.output))
        if directory:
            self.output = Path(directory)
            self.output_label.setText(directory)

    def build_request(self, dry_run=False):
        from nanomech.requests import ProbeOverrides, VeaRequest
        from nanomech.static import StaticConfig

        if self.sample is None:
            raise UiError("Sampleファイルを選択してください。")

        def optional_number(widget, label, integer=False):
            text = widget.text().strip()
            if not text:
                return None
            try:
                return int(text) if integer else float(text)
            except ValueError:
                raise UiError("{label}には整数を入力してください。" if integer else "{label}には数値を入力してください。", label=Message(label)) from None

        crop = self.crop_area.text().strip() or None
        if crop and not re.fullmatch(r"\s*\d+\s*,\s*\d+\s*:\s*\d+\s*,\s*\d+\s*", crop):
            raise UiError("Cropエリアは x_start,y_start:x_end,y_end で指定してください。")
        sensitivity = optional_number(self.sensitivity, "Sensitivity")
        probe = {"sensitivity": None if sensitivity is None else sensitivity * 1e-9,
                 "spring_constant": optional_number(self.spring_constant, "Spring constant")}
        probe_config = {}
        for name, (loaded_text, value) in self._loaded_probe.items():
            if getattr(self, name).text() == loaded_text:
                probe_config[name] = value
                probe[name] = None
        request = VeaRequest(
            sample=self.sample, calibration=self.calibration, output=self.output,
            static=StaticConfig(
                model=self.model.currentText(), fit_direction=self.fit_direction.currentText(),
                tip_radius=self.tip_radius.value() * 1e-9,
                cone_half_angle=self.cone_half_angle.value(), poisson_ratio=self.poisson_ratio.value(),
                baseline_start=self.baseline_start.value(), baseline_end=self.baseline_end.value(),
            ),
            probe=ProbeOverrides(**probe), probe_config=ProbeOverrides(**probe_config), config_path=self.config_path,
            probe_source="GUI", dry_run=dry_run,
            max_count=optional_number(self.max_count, "最大解析数", integer=True), crop_area=crop,
            plot_calibration=self.plot_calibration.isChecked(), plot_sample=self.plot_sample.isChecked(),
            max_plot_sample=(optional_number(self.max_plot_sample, "最大プロット数", integer=True)
                             if self.plot_sample.isChecked() else None),
            excitation=self.excitation.currentText(), correct_drag=self.correct_drag.isChecked(),
        )
        request.validate()
        return request

    def start_analysis(self, dry_run=False):
        if self.is_busy:
            return
        self.last_result = None
        self.progress.hide()
        self.progress_label.hide()
        try:
            request = self.build_request(dry_run)
        except (ValueError, TypeError) as error:
            self.status_label.set_message("入力を確認してください: {error}", error=error)
            return
        self.form.setEnabled(False)
        self.fit_button.setEnabled(False)
        self.dry_run_button.setEnabled(False)
        self.progress.show()
        self.progress.setRange(0, 0)
        self.progress_label.setText("処理段階: 準備中 | 処理済み点数: — | 進捗率: —")
        self.progress_label.show()
        self.status_label.setText("Dry-Run中…" if dry_run else "フィッティング中…")
        self.worker = VeaWorker(request, self)
        self.busy_changed.emit()
        self.worker.progress_changed.connect(self.update_progress)
        self.worker.finished.connect(self.finish_analysis)
        self.worker.start()

    @Slot(object)
    def update_progress(self, event):
        stages = {
            "selection": "解析範囲の確認", "calibration": "校正",
            "output_preparation": "保存先の準備", "calibration_plot": "校正プロット保存",
            "static": "静的解析", "dynamic": "動的解析", "moduli": "弾性率計算",
            "save_static": "静的解析結果の保存", "save_dynamic": "動的解析結果の保存",
            "save_results": "解析結果の保存", "complete": "処理終了",
            "dry_run_complete": "Dry-Run終了（校正）",
        }
        stage = stages.get(event.stage, event.stage)
        if event.total is None:
            self.progress.setRange(0, 0)
            detail = Message("処理済み点数: — | 進捗率: —")
        else:
            percent = event.percent
            self.progress.setRange(0, 1000)
            self.progress.setValue(round(percent * 10))
            self.progress.setFormat(f"{percent:.1f}%")
            detail = Message("処理済み点数: {completed} / {total} 点 | 進捗率: {percent:.1f}%",
                             dict(completed=event.completed, total=event.total, percent=percent))
        self.progress_label.set_message("処理段階: {stage} | {detail}", stage=Message(stage), detail=detail)

    @Slot()
    def finish_analysis(self):
        worker = self.worker
        if worker.error is not None:
            self.status_label.set_message("解析に失敗しました: {error}", error=worker.error)
            # Stop the indeterminate animation without implying 100% completion.
            self.progress.hide()
        else:
            result = worker.result
            self.last_result = result
            title = "Dry-Run" if worker.request.dry_run else "フィッティング"
            state = {"success": "完了", "partial_failure": "一部失敗", "failed": "失敗"}.get(result.status, result.status)
            output = Message("\n保存先: {path}", dict(path=result.output_dir)) if result.output_dir is not None else ""
            self.status_label.set_message(
                "{title}: {state}（選択 {selected} / {total} 点）{output}",
                title=Message(title), state=Message(state), selected=len(result.selection.point_indices),
                total=result.selection.total_count, output=output,
            )
        self.worker = None
        self.busy_changed.emit()
        worker.deleteLater()
        self.form.setEnabled(True)
        self.fit_button.setEnabled(self.sample is not None)
        self.dry_run_button.setEnabled(self.sample is not None)
