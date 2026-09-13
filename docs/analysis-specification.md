# 解析仕様・モデル・コマンド拡張の整理

作成日: 2026-09-12。仕様策定の初稿。コードの静的調査に基づき、解析結果の数値検証は未実施。
更新日: 2026-09-13。excitation-fitの旧コード準拠、run単位のJSON出力、measurementと対象点の選択規則をユーザー確認に基づき反映。

## 1. 目的と今回の範囲

- Nanosurfの旧スクリプトにあるVEA解析と励振係数計算を、再現可能でテスト可能なプログラムとして提供する。
- CLIは `python main.py <command> ...` とし、当初は `vea` と `excitation-fit` を提供する。以後のコマンド追加を可能にする。
- GUIは共通の解析サービスを呼ぶ。CLIの引数文字列を生成して解析する構成にしない。
- 並列化・CUDAは最終段階まで対象外。初期実装は逐次実行する。
- 本稿は仕様整理であり、ユーザー確認済みの要件と設計案を区別して記載する。API・配置・新しい設定は提案。実行コードは未実装。

調査元:

- [旧スクリプト](../v11Paul/demo_VEA_analysis_v11_evalCoeffsPolynom.py): import_data、demodulate_signal、evaluate_spec、evaluate_moduli、eval_coeffs_func、メイン処理。
- [nm_io.py](../nm_io.py): 読み込み、測定データ、SweepConfig、区間取得。
- [nm_models.py](../nm_models.py): NanomechModel、Linear、Sine、HertzSphere。
- [統合テスト](../tests/test_nm_integration.py)、[E2Eテスト](../tests/test_nm_end2end.py): 全解析の期待数値を保証する状態には至っていない。

## 2. コマンドとモデルは別の拡張単位

コマンドは「何を実行するか」、モデルは「どの数式で計算するか」を表す。

| 拡張対象 | 当初の候補 | 追加時の変更箇所 |
| --- | --- | --- |
| コマンド | vea、excitation-fit | コマンド固有の設定・ワークフロー・CLIアダプター・登録・テスト |
| 接触モデル | Hertz、Sneddon、Pyramid、DMT_Sphere、DMT_Cone | モデルの式・パラメータ・必要な形状定数・モデル登録・テスト |
| 信号モデル | 正弦波、ドリフト付き正弦波 | 信号モデルと復調設定・テスト |

新しい接触モデルを追加してもmain.pyへ分岐を追加しない。新しいコマンドを追加しても既存のワークフローを書き換えない。

### 構成案

```text
main.py                         # CLI起動のみ
main_gui.py                     # GUI起動のみ（後段で実装）
nanomech/
  cli.py                        # パーサー構築、登録済みコマンドのdispatch
  commands/
    registry.py                 # 明示的な組み込みコマンド登録
    vea.py                      # 引数定義、設定解決、VEAサービスへの接続
    excitation_fit.py           # 同上
  workflows/
    vea.py                      # VeaConfig -> VeaResult
    excitation_fit.py           # ExcitationFitConfig -> ExcitationFitResult
  ...                           # データ・モデル・I/O等は既存nm_群から段階的に整理
```

既存nm_モジュールを直ちに一括移動することは要件にしない。新しい公開APIの確定後に配置を整理する。

コマンド登録の契約案:

```python
# 概念例。名称・型の最終確定は実装時。
COMMANDS = (vea_command, excitation_fit_command)

for command in COMMANDS:
    subparser = subparsers.add_parser(command.name, help=command.summary)
    command.configure_parser(subparser)
    subparser.set_defaults(handler=command.execute_cli)

# 解析後に選択済みハンドラーを実行する。
# execute_cliは設定を解決・検証し、共通ワークフローを呼ぶ。
```

- 登録項目はname、summary、configure_parser、execute_cli。名前重複は起動時に検出する。
- 各コマンドは専用ConfigとResultを持つ。全コマンドの設定を1つの巨大なクラスに集めない。
- 実行設定は「明示されたCLI値 > config値 > デフォルト値」。未指定CLI値でconfigを上書きしない。
- configにはschema_versionとcommandを持たせる。CLIのコマンドと不一致ならエラーにする。
- main.pyは数値計算、コマンド名別のif/elif、個別モデルの選択を持たない。
- ワークフローはargparse、Qt、標準出力、対話ダイアログに依存しない。
- GUIは独自フォームから同じConfigを生成する。新コマンドのGUI対応はフォームを追加する作業として扱う。
- 最初は明示的な登録リストで十分。外部プラグインの自動探索は要件に含めない。

提案する呼び出し形:

```text
python main.py --help
python main.py vea --help
python main.py vea --config vea.toml
python main.py excitation-fit --config excitation.toml
```

追加例として将来 `force-fit` を設ける場合も、独立した設定・ワークフロー・登録を追加する。同コマンドの実装は今回の範囲外。

### measurementと対象点の選択

確認済み要件（2026-09-13）:

- 各NHFファイルで扱うmeasurementは先頭のindex=0のみ。measurement indexとその内部の測定点indexは区別する。
- `excitation-fit`は単一点／複数点にかかわらず測定点index=0のみを使用し、1組の6係数を出力する。max_points・crop_areaによる選択や、残りの点のゼロ埋めは適用しない。

以下の点選択規則はVEAのsample測定点に適用する:

- 単一点の場合は自動選択する。
- 複数点の場合、選択引数を省略すると全点を計算する。
- `max_points`（int）を指定すると最大点数で処理を終了し、残りの点の結果をゼロ埋めする。
- `crop_area`（str）を指定すると開始・終了XYインデックスで指定した範囲を計算し、範囲外の点の結果をゼロ埋めする。
- 元の全点数・マップ形状と点位置を保持する。cropは計算対象の限定であり、出力マップの切り詰めではない。ゼロ埋めは結果に適用し、入力波形を書き換えない。

VEAの範囲指定の確定仕様:

- crop文字列は `"x_start,y_start:x_end,y_end"`。XYは0始まり、開始・終了とも含める長方形とする。例: `"2,3:4,5"` は3×3点。
- 左下を(0,0)とし、右方向にX、上方向にYが増加する。生の取得順indexとXYを同一視しない。既存コードの変換はこの仕様に合わせて検証する。
- 併用時はcropで対象候補を選び、その候補を元の取得順で最大max_points点まで計算する。蛇行走査のXY順への並べ替えは行わない。
- max_pointsは正の整数。対象候補数以上なら全候補を処理する。0・負数は入力エラーにする。
- cropの形式不正、範囲外、開始>終了は入力エラーにし、暗黙の切り詰めや座標交換は行わない。
- 選択外／上限による未処理点はゼロとし、別の状態情報で未処理と成功値0を区別する。解析失敗は第3節に従ってNaNと状態・理由を記録する。

実装詳細の設計案:

- config/API名は `max_points`、`crop_area`。CLI表記は `--max_points`、`--crop_area` とし、ハイフン表記も別名として許容する案。
- 単一点も明示された選択引数は検証する。省略時は点0を自動選択する。
- max_pointsは成功点数ではなく処理を試みた点数の上限とする案。
- 選択処理は共通の機能として切り出し、CLIとGUIが同じ点集合を生成する。

VEAのcalibrationの確定仕様:

- 少なくとも1つのmeasurementを持ち、その先頭measurementに少なくとも1点のデータが保存されていることを前提とする。
- measurement index=0の測定点index=0のみを使用する。複数measurement・複数点があっても他のデータは使用しない。
- この1点を全sample対象点に対する共通のcalibrationとして使用する。sample用のmax_points・crop_areaとゼロ埋めはcalibrationへ適用しない。
- 入力検証ではmeasurementがない場合、または先頭measurementに点がない場合をエラーとし、別のmeasurement・点への代替は行わない。

## 3. veaの機能仕様

### 対応範囲の確定仕様（2026-09-13）

- 接触モデルは旧コードの5種類（Hertz、Sneddon、Pyramid、DMT_Sphere、DMT_Cone）をすべて対応必須とする。
- 励振方式はPiezoとCleanDriveの両方式を対応必須とする。接触モデルと励振方式は別の選択項目として扱う。
- この確定は対応範囲の指定であり、旧コードの単位不整合や未検証の数値結果を正解として承認するものではない。式・単位・結果の検証は継続する。
- 初回の実装・数値検証をHertzから始める案は維持するが、5モデルと両方式の対応完了まではVEA機能全体を完成扱いにしない。

### 感度・ばね定数の確定仕様（2026-09-13）

測定後の校正値変更に対応するため、sensitivityとspring_constantをそれぞれ独立に次の優先順位で解決する。

| 優先順位 | 採用元 |
| --- | --- |
| 1 | 明示された解析引数 `--sensitivity`、`--spring_constant` |
| 2 | configの `sensitivity`、`spring_constant` |
| 3 | sampleファイルの先頭measurementに格納された値 |
| 4 | calibrationファイルの先頭measurementに格納された値 |

- 引数とconfigの両方に値がある場合は、第2節の共通規則に従って明示された引数を優先する。引数／configで指定された値はファイル値に優先して強制適用する。
- sensitivityの単位はm/V、spring_constantの単位はN/m。
- ファイル属性はそれぞれ `spm_probe_calibration_deflection_sensitivity`、`spm_probe_calibration_spring_constant`。
- 一方のみ指定された場合、もう一方は独立に優先順位をたどる。2値が異なる由来でもよい。
- いずれかの値が引数・config・両ファイルのどこにも見つからない場合は例外をraiseして解析を中止する。既定の物理値で補わない。
- runログには各値の採用値・単位・由来を明記する。由来はCLI、config、sample、calibrationを区別し、config／ファイル由来ならそのパスとキー／属性名も記録する。
- 値の解決は各点の解析前に行う。片方が不足して中止した場合も、解決できた値の由来と不足項目をログに残す。

実装・検証事項:

- 未指定は明示的に表現し、旧コードの0を未指定とする規則へ依存しない。非有限値・非正値などの不正な指定はエラーにし、下位の値へ黙ってフォールバックしない案。
- 既にm/Nへ変換されたチャネルに新しい校正値を適用する際は、単なる単位変換と測定後の再校正を区別する。保存時の校正値が必要になる条件と不足時の扱いを検証する。
- excitation-fitはsampleとcalibrationの2入力を持たないため、単一入力ファイルをどの入力役割として解決するかはコマンド側の契約で明記する。上記VEAの優先順位を理由に第2の入力ファイルを必須にしない。

### 旧コードで確認できた入力と処理

- calibration NHFとmeasurement NHFのそれぞれ先頭のmeasurementを使用。calibrationの測定点は0固定。
- calibrationはVEAセグメント、measurementはAdvance・VEA・Retractを読み込む。Waitは任意の意図があるが、不在処理に不整合がある。
- Time、Deflection、Position Z、Sampler Meta Channel、offset・取得点数を使用。use_reference時はAnalyzer 2 Referenceも必要。
- 周波数は設定から線形／対数、昇順／降順で再構成。旧比較処理は7つのsweep設定の一致を要求する。
- Advanceの指定範囲でdeflection対Zの線形ベースラインを求め、各セグメントを補正。
- 押し込み量を `-(z + deflection)`、力を `spring_constant * deflection` として計算。
- AdvanceまたはRetractを接触モデルでフィットし、接触点を各セグメントの押し込み量から減算。
- 周波数ごとに波形を分割して復調し、振幅・位相・DC成分を得る。
- 必要に応じて参照チャネルとの位相差、流体抵抗補正を適用。
- 励振方式と接触形状に対応する式から複素弾性率を求める。
- 旧メインには全点解析・CSV・GWY出力のコードがあるが、現在はコメントアウトされている。

### 旧VEA式の記録（物理的妥当性の認定ではない）

`D`をdeflectionの複素振幅、`I`をindentationの複素振幅、添字rをcalibration、sをsampleとする。複素化は `A * exp(i*phase)`。use_reference時は各ファイルの参照位相を引く。

- 応答 `Q = Ds / Is`。correct_drag時は `Q -= Dr / Ir`。
- 球の係数 `B = (1-nu)*k / (4*sqrt(R)*sqrt(indentation_dc))`。
- 円錐の係数 `B = (1-nu)*k*pi / (8*tan(theta)*indentation_dc)`。
- 四角錐の係数 `B = (1-nu)*k / (2*sqrt(2)*tan(theta)*indentation_dc)`。
- Piezo: `G = B*Q`。CleanDrive: `G = B*(Dr/Ds - 1)`。
- `E = 2*(1+nu)*G`、貯蔵弾性率 `real(E)`、損失弾性率 `imag(E)`、損失正接 `imag(E)/real(E)`。
- 旧コードはoutput_idの文字列 `"1"` をCleanDriveとして扱う。CleanDrive分岐では補正済みQを使用していない。

### 入力不整合・解析失敗時の確定仕様（2026-09-13）

| 状況 | 動作 |
| --- | --- |
| calibrationとsampleの周波数・掃引設定が不一致 | 例外をraiseして中止。自動補間や共通周波数だけへの縮小は行わない |
| 必須セグメント・チャネルが欠落 | 例外をraiseして中止 |
| 任意のWaitセグメントがない | Waitを使う処理を省略して続行 |
| calibrationの解析に失敗 | 全体を中止 |
| sampleの静的フィットに失敗 | その点のVEA解析をスキップし、次の点へ進む |
| sampleの特定周波数で復調・物性計算に失敗 | その周波数の結果を失敗として記録し、他の処理は続行 |
| 全対象点で解析に失敗 | runを失敗扱いにする |

- 選択外・max_points上限による未処理は結果をゼロにする。解析失敗の結果はNaNにする。
- 値だけで判定せず、点・周波数ごとの状態情報と失敗理由を保存する。静的フィット失敗に伴うVEAスキップは、選択外の未処理と区別する。
- 一部成功したrunは「一部失敗」として結果を保存する。対象の解析がすべて成功した場合は成功とし、選択外／点数上限によるゼロ埋め自体を失敗扱いにしない。
- 有効に得られた他の点・周波数の結果は保持する。
- 感度・ばね定数の欠落による中止は前述の確定仕様に従う。
- この方針はVEAに適用する。excitation-fitの失敗時にNaNを係数JSONへ出力することは認めない。

実装時に具体化する項目: 状態コード、CLI終了コード、数値判定の許容差、出力形式ごとのNaN表現。JSONを使う箇所ではNaNリテラルを出力せず、nullと状態情報などの有効なJSON表現へ変換する。

### 提案する結果契約

- 点ごとの接触点、静的弾性率、該当時の付着パラメータ、snap-in・adhesionの力。
- 点×周波数ごとの貯蔵弾性率、損失弾性率、損失正接。
- 周波数、座標、単位、使用した設定と校正値の由来。
- 点・周波数ごとの成功／失敗と診断。全体成功、一部失敗、全体失敗を区別。
- 生の波形と結果は分離する。結果作成とファイル出力も分離する。

## 4. excitation-fitの機能仕様

### 確認済み要件（2026-09-13）

- 励振係数の計算仕様は旧コードどおりとする。
- 周波数はHz、`x = log10(f / Hz)`、対象振幅は復調したdeflection振幅A。`a = A / max(A)` で正規化する。
- `a = c0 + c1*x + c2*x**2 + c3*x**3 + c4*x**4 + c5*x**5` の5次多項式フィッティングで6係数を求める。係数の順序は定数項から昇順。
- 新しいSineのドリフト項や異なる正規化を無断で採用しない。旧処理を再現する検証を基準にし、解法変更は別の変更として扱う。
- 入力はNHFファイル。
- 最初のmeasurement（index=0）の最初の測定点（index=0）のみを使用する。ファイル内に複数点あっても、出力はその最初の点から求めた1組の6係数。残りの点の計算・集約・ゼロ埋めは行わない。
- 現状はユーザーが標準出力から係数を読み取っている。
- 新しい出力は、runごとのテキストファイルへ保存するJSON形式の6係数。

### 出力形式の設計案

- UTF-8の `excitation_coefficients.json` を各runの出力ディレクトリへ1ファイル保存する。拡張子.jsonのテキストファイルとする。
- 同じ入力を再実行してもrunを区別し、以前の結果を上書きしない。
- 係数はJSON数値として保存し、`c0` を定数項、`c5` を5次項とする。キーの並び順には依存しない。
- 標準出力には保存先や実行状態を表示できるが、係数を取り出すために標準出力を解析する必要はない。
- 失敗時は成功結果に見える係数ファイルを生成しない。NaNやInfinityを有効な係数として保存しない。
- 係数の表示用丸めは保存値に適用しない。

JSONの構造例（数値は説明用であり、計算結果ではない）:

```json
{
  "c0": 1.0,
  "c1": -0.2,
  "c2": 0.03,
  "c3": -0.004,
  "c4": 0.0005,
  "c5": -0.00006
}
```

logの底10、周波数Hz、振幅の最大値による正規化は確定仕様。正規化係数・適用範囲・診断値は下記の内部結果契約案で保持し、6係数ファイルへの追加や別ファイル保存の詳細は未確定。上記JSON例は単一点の1組分。

### 旧コードで確認した処理

旧eval_coeffs_funcが必要とするのはVEAの周波数掃引を含む1測定点であり、静的なAdvance/Retractのフォースカーブだけでは同処理を再現できない。

旧処理:

1. calibrationとして読み込まれたファイルの点0からVEA波形を取得。
2. deflection、indentation、Zを復調する。多項式の対象はdeflection振幅。
3. `Amax = max(A)`、`a = A/Amax` とする。
4. `x = log10(f)`として `a = c0 + c1*x + ... + c5*x**5` をフィット。
5. 非線形least_squaresを使用し、収束しなければcurve_fitへフォールバック。
6. 係数・誤差・正規化係数を標準出力へ表示し、図を表示する。

提案する内部結果契約（JSONファイルの必須出力は上記6係数）:

- c0～c5の6係数（定数項から昇順）、周波数単位Hz、logの底10を明記。
- 正規化係数Amaxとその単位、入力点、使用周波数範囲、有効点数、残差、収束状態。
- 不確かさが算出できない場合は「算出不能」とする。旧コードのように誤差0へ置換しない。
- 周波数の正値、有効周波数の数、設計行列のランク、正規化振幅の妥当性を検証する。
- 5次の6係数の識別には少なくとも6つの独立した周波数点が必要。残差から分散を推定するには正の残差自由度も必要。
- 装置向けの変換・逆応答化は旧多項式フィットとは別仕様。今回の入出力要件には含めず、JSON保存までを対象とする。

## 5. 数値モデルの棚卸し

以下は旧実装の式。`d = x-x0`とし、旧接触モデルはd<=0で0を返す。Eの物理的命名とgammaの定義は検証事項。

| モデル | d>0での旧式 | フィット変数 | 定数 | 現nm_models |
| --- | --- | --- | --- | --- |
| Linear | a*x+b | a,b | なし | 実装あり |
| Sine（旧） | A*sin(2*pi*f*t+phi-1)+b | A,f,phi,b | なし | 同一式ではない |
| Sine（現） | A*sin(2*pi*f*t+phi)+a*t+b | A,f,phi,a,b | なし | 実装あり |
| Hertz | 4*E*sqrt(R)*d**1.5 / (3*(1-nu**2)) | E,x0 | R,nu | HertzSphereあり |
| Sneddon | 2*E*tan(theta)*d**2 / (pi*(1-nu**2)) | E,x0 | theta,nu | 未実装 |
| Pyramid | E*tan(theta)*d**2 / (sqrt(2)*(1-nu**2)) | E,x0 | theta,nu | 未実装 |
| DMT_Sphere | Hertzの式 - 2*pi*R*gamma | E,x0,gamma | R,nu | 未実装 |
| DMT_Cone | E*tan(theta)*d**2/(1-nu**2) - 2*pi*gamma*d/tan(theta) | E,x0,gamma | theta,nu | 未実装 |
| 励振5次多項式 | sum(ci*log10(f)**i), i=0..5 | c0..c5 | 正規化係数 | 未実装 |

- nm_io.ContactModelNameのDMT_Cylinder、DMT_Tipは名前のみ。旧コードの5モデルとは別の追加候補で、対応済みとは扱わない。
- HertzSphereはignore_adhesionを定数に保持するが、現在のresidualsでは使用していない。旧モデルと同じ残差選択ではない。
- Sineの振幅・傾き・offsetの単位は入力チャネルに依存する。現在のメタデータのN固定を汎用仕様にしない。
- モデル登録は「識別名、変数と単位、必要定数、モデル生成」を扱う。接触形状に応じたVEA係数も明示的に対応付ける。
- モデル名が登録されていても、静的解析のみ対応／VEAまで対応を区別する。

## 6. 旧設定の記録

ここに記載する値は旧コードのデフォルト。excitation-fitは第4節の旧コード準拠を確定仕様とし、VEAについては新実装の確定値ではない。

| 分類 | 旧設定 |
| --- | --- |
| 校正 | sensitivity=0、spring_constant=0（0はファイル値を使用する意味） |
| 接触 | Hertz、Advance、R=5e-9 m、半角15度、nu=0.5 |
| ベースライン | Advanceの点数比率0.05～0.50 |
| 初期値 | indentation=100e-9 m、modulus=5e4 Pa、gamma=0.1（旧表記arb） |
| 制約・残差 | E=1～1e12、gamma=0～100、ignore_adhesion=True、ignore_baseline=True |
| 復調 | 中央40%、fは公称値の0.999～1.001倍、振幅>=0、位相0～2*pi |
| 補正 | use_reference=False、correct_drag=True |
| フィルタ | bessel_on_raw=False（実装はButterworth）、savitzky_golay_on_demod=False |
| 多項式 | 5次、振幅の最大値で正規化、周波数log10 |
| 描画 | moduli=True、transientの周波数index=19、spec=True。点数に応じた描画制限あり |

新設定は「物理定数」「解析条件」「ソルバー条件」「出力条件」に分け、校正値の未指定は0ではなく明示的な未指定として扱う案。校正ファイルと測定ファイルの値・上書き値は由来を保持する。

## 7. 仕様確定前に解決する事項

### 利用目的・装置仕様について確認が必要

確定済み: excitation-fitの旧コード準拠と点0からの6係数JSON出力、VEAのsample範囲指定（表記・両端包含・左下原点・併用順序・ゼロ埋め）、calibrationの先頭measurement内の点0のみ使用、旧コードの接触モデル5種類とPiezo／CleanDrive両方式への対応。詳細は第2～4節を参照。装置への設定操作は今回の対象外。

残る確認事項:

1. 第9節の代表入力に対する期待結果と、物理量ごとの許容誤差。入力ファイルの選定は確定済み。

感度・ばね定数の採用順位とrunログへの由来記録は第3節で確定済み。
VEAの入力不整合・解析失敗時の中止／継続、未処理ゼロ・失敗NaN、状態と理由の保存も第3節で確定済み。

### 実装調査・数値検証で解決する事項

- 単位: 旧evaluate_specはforce*1e9を渡す一方、モデル側の1e9係数はコメントアウトされている。旧静的弾性率を無条件に正解としない。
- 校正: 旧コードは最初に読み込んだ校正値をグローバルに再使用する。m/Nチャネルの再校正方式も現convert_deflection_to_metersと異なる。
- 区間: find_frequency_changesの相対／絶対位置、先頭・終端と末尾2点除外の根拠。offsetフォールバックのN+1境界とN個の点数の整合性。
- 位相: 旧Sineのphi-1と現Sineのphi、ドリフト追加、位相unwrapと損失弾性率の符号への影響。
- Wait: 旧import_dataのwait_existsはローカル代入であり、後段には不在時もWaitを参照する箇所がある。
- 前処理: 旧VEAでは補正したindentationに対し、deflectionは元チャネルから取得している。復調対象の整合性を確認する。
- モデル: E_effという変数名と1/(1-nu**2)を含む式の意味、DMT gammaの定義・単位、DMT_Coneの係数を確認する。
- 周波数: 不一致時は中止する確定仕様に従い、設定値の比較方法・数値許容差を具体化する。共通周波数のみの解析・補間は現在の対象外。
- 不正値: 欠損、短い区間、非正の押し込みDC、ゼロに近い複素分母の検出条件を定め、第3節の失敗処理につなぐ。
- 座標: 旧／現コードの走査起点・XY反転の違いを非正方形マップで検証する。

## 8. この仕様整理の完了条件

- 2コマンドの必須入力、設定、出力、適用モデルが確定している。
- 旧挙動を維持する項目、修正する項目、後回しにする項目を区別できる。
- 代表入力と比較対象が決まり、物理量ごとに許容誤差を設定できる。
- コマンド登録とモデル登録の責務が合意され、GUIや新コマンドを追加しても計算を複製しない。
- 上記を満たしてからデータ契約・設定クラス・ワークフローの実装に進む。

## 9. 代表検証データ（確定）

データはリポジトリ直下の `test-data-large/` に保存し、Git管理対象から除外する。ファイル名と用途は本仕様で管理する。

| 用途 | リポジトリからの相対パス | 確認時のサイズ（bytes） |
| --- | --- | ---: |
| excitation-fit | test-data-large/VEA-power-corr.nhf | 985688 |
| VEA calibration | test-data-large/VEA-500-5k-calibration.nhf | 616088 |
| VEA sample | test-data-large/VEA-500-5k-sample.nhf | 7261109032 |

- 2026-09-13に3ファイルの配置を確認。`.gitignore` の `test-data-large/` により除外されており、Git追跡対象ではない。
- ファイルの存在とサイズのみ確認済み。内部のチャネル・設定・点数や計算結果は未検証。ファイル名から内容や励振方式を断定しない。
- excitation-fitは先頭measurementの点0、VEA calibrationも先頭measurementの点0を使用する。VEA sampleは確定した範囲指定規則に従う。
- 代表入力の指定は期待数値の確定を意味しない。6係数、静的解析、周波数ごとの物性値について、比較対象・許容誤差を別途設定する。
- 大容量sampleを使う検証は、小さいmax_pointsまたはcrop_areaによる検証から始め、その後に全点へ広げる案。点数制限だけで読み込みメモリが減るとは限らないため、Readerの読み込み方式も調査する。
- テスト運用案: ローカル大容量データを用いる検証と小規模な通常テストを分離する。データ不在時は大容量テストを明示的にskipし、実行していない検証を成功扱いにしない。
