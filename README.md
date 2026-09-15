# nanomech_nhf

Nanosurf AFMのNHFファイルから、静的ヤング率と周波数ごとの粘弾性を解析するPython CLIです。
入力、校正、フィッティング、CSV・Gwyddion・PNG出力までを非対話で実行します。

## 環境のインストール

Python 3.12以上が必要です。以下の手順はWindows PowerShellを例にしています。リポジトリを取得した後、リポジトリのルートディレクトリで実行してください。

### GUIを含むすべての環境

GUIとCLIの両方を使用する場合は、仮想環境を作成してGUIオプション付きでこのプロジェクトをインストールします。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[gui]"
```

PowerShellでスクリプト実行が制限されている場合は、現在のユーザーだけ一時的に許可してから仮想環境を有効化できます。

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

インストール後の起動方法:

```powershell
python -m nanomech_gui
# または
nanomech-gui
```

### CLIのみの環境

GUIを使用しない場合は、GUI依存のPySide6を含めずにインストールできます。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

CLIの起動確認:

```powershell
python main.py --help
python main.py vea --help
python main.py excitation-fit --help
```

`-e` は編集可能インストールです。ソースコードを変更した場合も、同じ仮想環境からそのまま実行できます。
GUI付きで後からインストールし直す場合は `python -m pip install -e ".[gui]"` を実行してください。

### テスト用の追加パッケージ

テストを実行する場合は、解析環境を有効化した状態で次を実行します。

```powershell
python -m pip install pytest Pillow
python -m pytest
```

## VEA解析を実行する

設定例の [examples/vea.toml](examples/vea.toml) に入力パスや解析条件を設定して実行します。
この例では先頭4点を解析し、校正・試料のPNGも保存します。

```powershell
python main.py --config examples/vea.toml
```

CLI引数だけでも実行できます。

```powershell
python main.py vea --sample test-data-large/VEA-500-5k-sample.nhf --calibration test-data-large/VEA-500-5k-calibration.nhf --max-count 4 --output results
```

通常の `vea` は、校正点0の処理、試料の静的解析、周波数ごとの正弦波フィット、粘弾性計算、結果出力を順に実行します。
`--max-count` と `--crop-area` を省略すると全点を解析します。

実行前に校正と対象点だけを確認する場合:

```powershell
python main.py vea --sample test-data-large/VEA-500-5k-sample.nhf --calibration test-data-large/VEA-500-5k-calibration.nhf --max-count 4 --crop-area "0,0:1,1" --dry-run --plot-calibration
```

`--dry-run` は試料のメタデータ、プローブ定数、校正波形のフィット・周波数検証まで実行します。
試料波形の読み込み・解析、CSV・GWY・`run.json` の保存は行いません。
`--plot-calibration` を併用すると校正PNGを保存します。指定しなければ結果ディレクトリは作成しません。
校正キャッシュはdry-runでも更新されます。

## 設定ファイルと優先順位

TOMLとJSONに対応します。`schema_version = 1` と `command = "vea"` または `"excitation-fit"` が必須です。
`--config` のみで起動するとファイル内の `command` が選択されます。
サブコマンドを明示する場合は、ファイル内の指定と一致させてください。

VEA用TOMLのテーブル:

| テーブル | 設定キー |
|---|---|
| `[cli]` | `sample`, `calibration`, `output`, `max_count`, `crop_area`, `log_level`, `dry_run`, `plot_calibration`, `plot_sample`, `max_plot_sample`, `excitation`, `correct_drag` |
| `[probe]` | `tip_radius`, `cone_half_angle`, `poisson_ratio`, `sensitivity`, `spring_constant` |
| `[static]` | `fit_direction`, `model`, `baseline_start`, `baseline_end` |

優先順位は **明示したCLI引数 → 設定ファイル → 既定値** です。
感度・ばね定数については、未指定時にNHFメタデータを使用します。
不明なキー、設定の重複、型や選択肢の誤りはエラーになります。
旧名 `max_points` も使用できますが、`max_count` と同時には指定できません。
JSONではトップレベルに各設定キーを置く従来形式も使用できます。

相対パスの基準は次のとおりです。

| 指定方法 | 基準ディレクトリ |
|---|---|
| TOML内のパス | TOMLファイルのあるディレクトリ |
| CLI引数・JSON内のパス | コマンドの実行ディレクトリ |

Windowsパスには `/`、またはTOMLのシングルクォート文字列を使用できます。
設定を上書きする例:

```powershell
python main.py --config examples/vea.toml --model DMT_sphere --fit-direction retract --max-count 4 --log-level DEBUG
python main.py --config examples/vea.toml --no-plot-sample --no-plot-calibration
```

結果ディレクトリを作成する実行では、指定した元の設定ファイルを `input_config.toml` または `input_config.json` としてコピーします。
このコピーはCLIで上書きした後の設定ではありません。通常解析の採用条件は `run.json` も参照してください。

## 主なVEAオプション

| オプション | 内容・既定値 |
|---|---|
| `--sample` | 試料NHF。CLIまたは設定ファイルで必須 |
| `--calibration` | 校正NHF。未指定なら前回のキャッシュ |
| `--output` | 出力先の親ディレクトリ。既定値 `results` |
| `--max-count` | crop後に解析を試みる点数の上限。正の整数、未指定は全点 |
| `--crop-area` | `"x_start,y_start:x_end,y_end"`。左下原点、0始まり、両端を含む |
| `--model` | `Hertz`（既定）、`Sneddon`, `Pyramid`, `DMT_Sphere`, `DMT_Cone` |
| `--fit-direction` | `Advance`（既定）または `Retract` |
| `--tip-radius` | 先端半径、既定値 `5e-9` m |
| `--cone-half-angle` | 円錐・角錐の半角、既定値15度。0より大きく90未満 |
| `--poisson-ratio` | ポアソン比、既定値0.5。範囲は `-1 < ν <= 0.5` |
| `--baseline-start` / `--baseline-end` | Advanceデータに対するベースライン区間比率。既定値0.05 / 0.50 |
| `--sensitivity` | 感度、m/V。正の有限値 |
| `--spring-constant` | ばね定数、N/m。正の有限値 |
| `--excitation` | `auto`（既定）、`Piezo`, `CleanDrive` |
| `--no-correct-drag` | 既定で有効なPiezoのドラッグ補正を無効化 |
| `--plot-calibration` | 校正の正弦波フィットPNGを保存。既定は無効 |
| `--plot-sample` | 試料の静的・動的フィットPNGを保存。既定は無効 |
| `--max-plot-sample` | 試料PNGの点数上限。未指定は対象成功点すべて、0は保存なし |
| `--dry-run` | 校正と対象点の確認まで。既定は無効 |
| `--log-level` | `DEBUG`, `INFO`（既定）, `WARNING`, `ERROR`, `CRITICAL` |

モデル名・解析方向・ログレベルは大文字小文字を区別しません。
`--max_count`, `--max_points`, `--max-points` は `--max-count` の別名です。
`--crop_area`, `--spring_constant`, `--log_level` などの別名も使用できます。全指定は `vea --help` を参照してください。
ログレベルはサブコマンドの前後どちらでも指定できます。

cropを先に適用し、その後に元の取得順で点数制限を適用します。
出力のマップサイズはcropや点数制限で縮小せず、元の寸法を保持します。
現在のマップ選択は左下からの蛇行走査に対応します。範囲外・逆転したcropはエラーです。

## 校正と解析仕様

### 校正ファイルとプローブ定数

`--calibration` または設定ファイルの校正パスを指定した場合、メタデータ検証後にNHF本体を
ルートの `.last_calibration.nhf` へコピーします。未指定時は実行ディレクトリに関係なく、このキャッシュを使用します。
明示した入力に問題がある場合、キャッシュへフォールバックせずエラーになります。
キャッシュ更新は原子的に行い、コピー失敗時は以前のキャッシュを保持します。
更新は波形フィット前なので、その後に周波数検証が失敗する場合もあります。

感度とばね定数はそれぞれ独立に **CLI → 設定ファイル → 試料NHF → 校正NHF** の順に解決し、値・単位・出典を記録します。
変位・力として保存されたdeflectionは元の校正値で検出器電圧に戻し、採用した感度で変位に再換算します。
力はその変位と採用したばね定数から算出します。

校正は最初のmeasurementの点0を使用します。試料と校正のスイープ条件が一致しない場合は停止します。

### 静的解析

Advanceの指定比率区間でZに対する線形ベースラインを求め、AdvanceとRetractの両方から差し引きます。
選択した方向の力・押込み量から、ヤング率と接触位置を推定します。内部単位はN・m・Paです。

5種類の接触モデルは [nanomech/nm_models.py](nanomech/nm_models.py) に実装され、解析ヤコビアン、
パラメータスケーリング、残差の正規化を使用します。
非付着モデルは正の力を持つデータを使用します。DMTモデルは全曲線の残差と複数の接触位置初期値を使用し、
付着パラメータ `adhesion_parameter_n_per_m` も推定します。非付着モデルではこの値は0です。

### 正弦波フィットと周波数検証

各周波数区間の中央40%を使用し、ドリフトを0に固定します。
位相は `sin(2*pi*f*t + phase - 1)` の規約で計算し、周波数方向にunwrapします。

校正deflectionから周波数を推定し、NHF設定値との相対誤差が5%を超えると停止します。
推定時の探索範囲は設定周波数の0.5〜1.5倍です。推定値と誤差はINFOログに出力します。
検証後の校正全チャンネルと試料は、NHF周波数を固定し、正規化したsin・cos・DCの線形最小二乗でフィットします。
CSVの `*_fitted_frequency_hz` は最終フィットに使ったNHF周波数です。

対象チャンネルはdeflection、indentation、position_zです。
試料deflectionには感度と静的ベースライン補正を適用し、indentationは `-(Z + corrected_deflection) - contact_point` です。
試料波形は点ごとの範囲を読み込みます。静的解析に失敗した点は動的解析をスキップします。
周波数・チャンネル単位のフィット失敗を記録し、後続の処理は継続します。位相unwrapは失敗区間でリセットします。

### 粘弾性計算

`auto` は試料のスイープ設定 `output_id` が1ならCleanDrive、それ以外はPiezoを選択します。
Piezoは試料のdeflection/indentation応答比から校正の応答比を差し引きます。
`--no-correct-drag` で校正項を省略できます。CleanDriveは校正/試料のdeflection比から1を引き、Piezoのドラッグ補正は適用しません。

Hertzでは、複素deflectionをD、複素indentationをI、試料のindentation DCをdとすると、
`B = (1-ν)*k / (4*sqrt(R)*sqrt(d))`、`E* = 2*(1+ν)*B*Q` です。
QはPiezoで `Ds/Is - Dr/Ir`、CleanDriveで `Dr/Ds - 1` です（s:試料、r:校正）。
選択モデルにより球・円錐・角錐の形状係数を使用します。
実部・虚部を貯蔵弾性率・損失弾性率とし、その比を損失正接とします。
押込みDCが非正、分母が数値的に無視できる場合などは失敗として記録します。
参照チャンネルによる位相補正は未実装です（`use_reference=false`）。

## 出力ファイル

出力先には実行ごとにUTC日時とUUIDによるディレクトリを作成します。
通常VEA解析の出力は次のとおりです。

| ファイル | 内容 |
|---|---|
| `static_results.csv` | 元の各点につき1行。ヤング率、接触位置、DMT Gamma、snap-in力、付着力、ベースライン、状態・失敗理由 |
| `vea_fit_results.csv` | 元の各点×周波数につき1行。3チャンネルの振幅・周波数・位相・DC・残差と状態 |
| `vea_results.csv` | 動的フィット結果に静的結果、貯蔵・損失弾性率、損失正接、計算状態を追加 |
| `<sample名>_VEAnalysis.gwy` | CSVと同じ解析値の空間マップ。通常解析で自動保存 |
| `run.json` | 入力、校正元、採用条件、プローブ出典、選択点数、各解析段階の状態 |
| `input_config.toml` / `input_config.json` | 設定ファイルを指定した場合の原本コピー |
| `calibration/calibration_deflection.png` | `--plot-calibration` 指定時。全周波数を縦に並べた校正波形とフィット |
| `sample/sample_point<index>_<model>_<segment>.png` | `--plot-sample` 指定時の試料フィット図 |

CSVは元の取得順、動的テーブルは取得順・スイープ順で出力します。
未選択点は数値0・`unprocessed`、失敗した解析値は`NaN`と状態・失敗理由を保持します。
段階によって `failed`、`skipped_static_failed`、`skipped_fit_failed` などを記録します。

GWYは静的5チャンネルと周波数ごとの貯蔵弾性率・損失弾性率・損失正接を保存し、5周波数なら合計20チャンネルです。
未処理点は0、非有限値はNaNとマスクで保持します。
NHFのX/Y範囲とscanner offsetを同名の軸に設定し、蛇行走査をXYへ復元してY方向を反転したラスタを保存します。
軸交換は行いません。scanner rotationはメタデータに保存し、回転・補間は行いません。

試料の静的PNGは選択モデルの力–押込み曲線を、動的PNGは全周波数のdeflection–時間フィットを縦に並べます。
名前の例は `sample_point00000_Hertz_advance.png` と `sample_point00000_sine_VEA.png` です。
indexの桁数は元の総点数の桁数に合わせます。
`--max-plot-sample` は静的・動的PNGにそれぞれ独立に適用し、解析点数やCSVには影響しません。
この上限だけを指定しても描画は有効になりません。描画時の波形再読み込み・再フィットは行いません。

最終粘弾性計算の状態が `failed` なら終了コード1、`success` または `partial_failure` なら0です。
入力・校正などの処理エラーは1、argparseの引数構文エラーは2になります。
部分成功でも0になるため、自動処理では終了コードだけでなく `run.json` とCSVの状態列も確認してください。
準備や出力の途中で失敗した場合、すべての成果物が揃うとは限りません。

## 励振補正係数の計算

```powershell
python main.py excitation-fit --input test-data-large/VEA-power-corr.nhf --output results
```

最初のmeasurementの点0を用い、周波数ごとの振幅を最大振幅で正規化して5次多項式にフィットします。
式は `amplitude / max(amplitude) = sum(ci * log10(frequency_Hz)**i)`、係数はc0〜c5です。
少なくとも6組の周波数・振幅と、ランク6の設計行列が必要です。
出力は `excitation_coefficients.json` と、単位・校正スケール・フィット診断値を含む `run.json` です。

TOML設定例:

```toml
schema_version = 1
command = "excitation-fit"

[cli]
input = "../test-data-large/VEA-power-corr.nhf"
output = "../results"
log_level = "INFO"
```

この相対パス例は `examples/` に置く場合の指定です。
励振係数計算の復調は旧実装互換の方式を保持し、VEAの5%周波数検証・固定周波数フィットとは別です。
生成した係数JSONを `vea` が自動で読み込む機能はありません。

