"""Session-local GUI translations, independent of analysis settings."""
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QAbstractButton, QGroupBox, QLabel, QLineEdit, QWidget


ENGLISH = {
    "解析設定の読み込み": "Load analysis settings",
    "設定ファイルを読み込むと、対応するタブの解析条件を更新します。": "Load a settings file to update the corresponding analysis tab.",
    "解析設定を読み込む": "Load analysis settings",
    "解析設定 (*.toml *.json);;TOML (*.toml);;JSON (*.json)": "Analysis settings (*.toml *.json);;TOML (*.toml);;JSON (*.json)",
    "設定を読み込めませんでした: {error}": "Could not load settings: {error}",
    "読み込み済み: {path}{note}": "Loaded: {path}{note}",
    "\nDry-Run設定です。Dry-Runボタンで実行してください。": "\nDry run is configured. Use the Dry-Run button to run it.",
    "解析中です。完了後にウィンドウを閉じてください。": "Analysis is running. Please close the window after it finishes.",
    "Calibrationを選択": "Select calibration",
    "Sampleを選択": "Select sample",
    "保存先を選択": "Select output folder",
    "未選択（保存済み校正キャッシュを使用）": "Not selected (use cached calibration)",
    "未選択": "Not selected",
    "空欄：全点": "Blank: all points",
    "x_start,y_start:x_end,y_end（空欄：全域）": "x_start,y_start:x_end,y_end (blank: full area)",
    "空欄：全点、0：出力なし": "Blank: all points; 0: no plots",
    "最大解析数": "Maximum points",
    "Cropエリア": "Crop area",
    "プロット出力": "Save plots",
    "最大Sampleプロット数": "Maximum sample plots",
    "最大プロット数": "Maximum plots",
    "プローブ情報": "Probe",
    "空欄：NHFから取得": "Blank: use NHF metadata",
    "先端形状": "Tip shape",
    "先端半径 (nm)": "Tip radius (nm)",
    "先端半角 (°)": "Tip half-angle (°)",
    "球": "Sphere",
    "円錐": "Cone",
    "四角錐": "Pyramid",
    "フィッティングセグメント": "Fitting segment",
    "モデル": "Model",
    "ポアソン比": "Poisson ratio",
    "ベースライン開始（比率）": "Baseline start (fraction)",
    "ベースライン終了（比率）": "Baseline end (fraction)",
    "流体抵抗補正を適用（Piezo）": "Apply hydrodynamic drag correction (Piezo)",
    "励振方式": "Excitation method",
    "周波数・スイープ条件はNHFファイルから取得します。": "Frequency and sweep settings are read from the NHF file.",
    "フィッティングを開始": "Start fitting",
    "Cropエリアは x_start,y_start:x_end,y_end で指定してください。": "Specify the crop area as x_start,y_start:x_end,y_end.",
    "Cropエリアの開始座標は終了座標以下にしてください。": "Crop start coordinates must not exceed the end coordinates.",
    "設定値をGUIの表示単位に変換できません。": "Settings cannot be converted to the display units.",
    "設定を読み込みました。": "Settings loaded.",
    "Sampleファイルを選択してください。": "Please select a sample file.",
    "{kind} NHFを選択": "Select {kind} NHF file",
    "NHFファイル (*.nhf *.NHF)": "NHF files (*.nhf *.NHF)",
    "{label}には整数を入力してください。": "Enter an integer for {label}.",
    "{label}には数値を入力してください。": "Enter a number for {label}.",
    "入力を確認してください: {error}": "Please check the input: {error}",
    "処理段階: 準備中 | 処理済み点数: — | 進捗率: —": "Stage: Preparing | Processed points: — | Progress: —",
    "Dry-Run中…": "Dry run in progress…",
    "フィッティング中…": "Fitting in progress…",
    "解析範囲の確認": "Checking analysis range",
    "校正": "Calibration",
    "保存先の準備": "Preparing output folder",
    "校正プロット保存": "Saving calibration plots",
    "静的解析": "Static analysis",
    "動的解析": "Dynamic analysis",
    "弾性率計算": "Calculating moduli",
    "静的解析結果の保存": "Saving static results",
    "動的解析結果の保存": "Saving dynamic results",
    "解析結果の保存": "Saving analysis results",
    "処理終了": "Processing finished",
    "Dry-Run終了（校正）": "Dry run finished (calibration)",
    "処理済み点数: — | 進捗率: —": "Processed points: — | Progress: —",
    "処理済み点数: {completed} / {total} 点 | 進捗率: {percent:.1f}%": "Processed points: {completed} / {total} | Progress: {percent:.1f}%",
    "処理段階: {stage} | {detail}": "Stage: {stage} | {detail}",
    "解析に失敗しました: {error}": "Analysis failed: {error}",
    "フィッティング": "Fitting",
    "完了": "Completed",
    "一部失敗": "Partially failed",
    "失敗": "Failed",
    "{title}: {state}（選択 {selected} / {total} 点）{output}": "{title}: {state} (selected {selected} / {total} points){output}",
    "\n保存先: {path}": "\nOutput folder: {path}",
    "NHFファイルを選択": "Select NHF file",
    "ファイルが選択されていません": "No file selected",
    "次数": "Degree",
    "係数": "Coefficient",
    "{degree}次 (c{degree})": "{degree} (c{degree})",
    "設定を読み込みました。フィッティングを開始できます。": "Settings loaded. Ready to start fitting.",
    "NHFファイルを選択してください。": "Please select an NHF file.",
    "フィッティングに失敗しました: {error}": "Fitting failed: {error}",
    "フィッティングが完了しました。": "Fitting completed.",
}


@dataclass(frozen=True)
class Message:
    source: str
    values: dict = field(default_factory=dict)


class UiError(ValueError):
    """A validation error that can be retranslated after it is displayed."""
    def __init__(self, source, **values):
        self.message = Message(source, values)
        super().__init__(source)


class Translator(QObject):
    changed = Signal()

    def __init__(self, parent=None, language="ja"):
        super().__init__(parent)
        self.language = language

    def text(self, source, **values):
        template = ENGLISH.get(source, source) if self.language == "en" else source
        resolved = {}
        for key, value in values.items():
            if isinstance(value, UiError):
                value = value.message
            resolved[key] = self.text(value.source, **value.values) if isinstance(value, Message) else value
        return template.format(**resolved) if values else template

    def set_language(self, language):
        if language not in ("ja", "en"):
            raise ValueError(f"Unsupported UI language: {language}")
        if language != self.language:
            self.language = language
            self.changed.emit()

    def bind_tree(self, root):
        """Bind static captions once; editable values and file paths are untouched."""
        for widget in root.findChildren(QWidget):
            if isinstance(widget, LocalizedLabel):
                widget.bind(self)
                continue
            if widget.property("translation_bound"):
                continue
            if isinstance(widget, (QAbstractButton, QLabel)):
                source, setter = widget.text(), widget.setText
            elif isinstance(widget, QGroupBox):
                source, setter = widget.title(), widget.setTitle
            elif isinstance(widget, QLineEdit):
                source, setter = widget.placeholderText(), widget.setPlaceholderText
            else:
                continue
            if source in ENGLISH:
                widget.setProperty("translation_bound", True)
                def refresh(source=source, setter=setter):
                    setter(self.text(source))
                self.changed.connect(refresh)
                refresh()


class LocalizedLabel(QLabel):
    """Retain message templates so status/progress text can switch live."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.message = Message(text)
        self.translator = None

    def bind(self, translator):
        if self.translator is translator:
            return
        if self.translator is not None:
            self.translator.changed.disconnect(self.refresh)
        self.translator = translator
        translator.changed.connect(self.refresh)
        self.refresh()

    def set_message(self, source, **values):
        self.message = Message(source, values)
        self.refresh()

    def setText(self, text):
        self.set_message(text)

    def clear(self):
        self.set_message("")

    def refresh(self):
        message = self.message
        text = self.translator.text(message.source, **message.values) if self.translator else message.source
        super().setText(text)
