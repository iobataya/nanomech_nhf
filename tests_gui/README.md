# GUI tests

Qt6 GUI専用テストの配置先です。`test_startup.py` はWindowsのCOM初期化順序を検証します。
`test_progress.py` はワーカー実行中の点数・進捗率表示と、エラー時の復帰を検証します。
`test_config.py` は設定読み込み、パス・単位変換、既定値への復帰、不正設定時の入力保持を検証します。
`test_i18n.py` は日本語・英語の切り替えと、設定値・係数・進捗の保持を検証します。
`python -m pytest tests_gui -q` で実行します（PySide6未導入時はスキップ。COMテストはWindows専用）。
共通APIの動作は `tests/` のCLI経由のテストで確認します。
