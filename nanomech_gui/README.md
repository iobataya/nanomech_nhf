# GUI

Qt6（PySide6）によるGUIです。メインウィンドウには `VEA` と `excitation-fit` の
2つのタブがあり、起動時は `VEA` を表示します。

画面右上の「Language / 言語」で **日本語 / English** を切り替えられます。
ボタン、入力ラベル、先端形状、係数テーブルの見出し、進捗・状態メッセージをその場で更新します。
解析中も切り替え可能で、選択ファイル・解析条件・計算結果は保持します。
初期表示は日本語です。言語選択は現在のウィンドウ内で有効で、設定ファイルには保存しません。
ファイル選択ダイアログのOS標準ボタンや外部ライブラリ由来のエラー本文は、OS・ライブラリの言語に従います。

To use the English interface, select **English** from **Language / 言語** at the top right.
Both tabs, progress messages, and application controls update immediately without changing your analysis settings or results.

タブの上にある「解析設定の読み込み」からTOML／JSONを選択できます。
CLIと同じ `schema_version = 1` と `command = "vea"` または `"excitation-fit"` を指定してください。
対応するタブに切り替わり、設定値をフォームへ反映します。読み込みだけでは解析を開始しません。
未指定項目は既定値に戻し、ファイルパス未指定なら未選択に戻します。
TOMLの相対パスは設定ファイルの場所を基準に解決し、JSONはCLI互換で作業ディレクトリ基準です。
Sensitivityと先端半径はSI単位からGUIのnm単位に変換し、モデルに合わせて先端形状も切り替えます。
不正な設定の場合は現在の入力を保持してエラーを表示します。解析中は読み込みできません。
`dry_run=true` は上部に案内を表示するので、Dry-Runボタンで実行してください。
`log_level` はCLI用、excitation-fitの `output` はCLI保存用で、GUIの入力項目にはありません。
VEAでは読み込んだ設定を解析結果とともに保存します。読み込み後に編集した条件はGUIの値を使用します。

VEAタブの入力項目:

- Files：Calibration、Sample、保存先。Calibration未選択時は既存の校正キャッシュを使用します。
- Analysis Range：最大解析数、cropエリア、校正・試料のPNG出力、最大試料プロット数。
  最大数の空欄は全点、cropの空欄は全域です。最大プロット数の0は出力なしです。
- プローブ情報：Sensitivity（nm/V）、Spring constant（N/m）、先端形状、先端半径（nm）、先端半角（°）。
  SensitivityとSpring constantの空欄はNHFの値を使用します。APIへ渡す際にnmをmへ変換します。
- Static：Advance／Retract、形状に対応するモデル、ポアソン比、ベースライン範囲（0～1）。
- Dynamic：励振方式（auto／Piezo／CleanDrive）、Piezoの流体抵抗補正。
  周波数・スイープ条件はNHFから取得します。

「フィッティングを開始」で解析と保存、「Dry-Run」で対象点の選択・校正の確認を実行します。
どちらもバックグラウンドで実行し、完了状態・選択点数・保存先、またはエラーを表示します。
Dry-Runでも校正キャッシュは更新されます。Calibrationのプロットを指定すると校正PNGも保存します。
計算中は条件変更・再実行・ウィンドウ終了を抑止します。

実行中は処理段階、処理済み点数、段階ごとの進捗率を表示します。
校正は1点、静的解析・動的解析・弾性率計算は選択した点数を分母にします。
処理済み点数には失敗・スキップも含み、弾性率計算は全周波数の処理が終わると1点として数えます。
保存など点数で測れない段階では点数・率を「—」とし、バーは処理中表示になります。
進捗率は段階ごとにリセットされ、解析全体の所要時間に対する割合ではありません。
大きなマップでも画面更新が滞らないよう、点数表示の更新は最大約10回/秒（段階切り替え・最終更新を除く）です。

`excitation-fit` タブでは「NHFファイルを選択」でファイルを指定するとパスを表示し、
「フィッティングを開始」で0～5次の係数（c0～c5）を2列のテーブルに表示します。
係数は `x = log10(f / Hz)` に対する昇べき順です。
計算中はファイル選択・再実行を無効にし、失敗時はエラーを表示して再実行可能な状態に戻します。
別ファイルの選択や再実行時には前の結果をクリアします。計算完了後にウィンドウを閉じられます。

```powershell
pip install -e ".[gui]"
python -m nanomech_gui
# または nanomech-gui
```

`app.py` はアプリケーション起動、`main_window.py` はウィンドウとタブの構成を担当します。
CLIのみ利用する場合、GUI用の追加依存は不要です。

`excitation_fit_tab.py` がファイル選択・係数表示・ワーカースレッドを担当し、
保存を伴わない共通API `nanomech.workflows.excitation_fit` を呼び出します。
CLIの `run_excitation_fit` も同じ解析APIを利用しています。
`vea_tab.py` は条件を `VeaRequest` に変換し、`run_vea` をワーカースレッドから呼び出します。
Qtのimport、シグナル、ウィジェットはこのパッケージ内に限定します。

翻訳は `i18n.py` に集約しています。内部のモデル名・形状IDと表示名を分け、
動的メッセージはテンプレートと値を保持して言語変更時に再描画します。
