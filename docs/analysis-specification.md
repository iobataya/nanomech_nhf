# 解析仕様・モデル・コマンド拡張の整理

作成日: 2026-09-12。仕様策定の初稿。コードの静的調査に基づき、解析結果の数値検証は未実施。
更新日: 2026-09-13。excitation-fitの入力とrun単位のJSON出力をユーザー確認に基づき反映。

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

## 3. veaの機能仕様

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

### 提案する結果契約

- 点ごとの接触点、静的弾性率、該当時の付着パラメータ、snap-in・adhesionの力。
- 点×周波数ごとの貯蔵弾性率、損失弾性率、損失正接。
- 周波数、座標、単位、使用した設定と校正値の由来。
- 点・周波数ごとの成功／失敗と診断。全体成功、一部失敗、全体失敗を区別。
- 生の波形と結果は分離する。結果作成とファイル出力も分離する。

## 4. excitation-fitの機能仕様

### 確認済み要件（2026-09-13）

- 周波数の対数と振幅の5次多項式フィッティングにより6係数を求める。
- 入力はNHFファイル。
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

logの底10、周波数Hz、振幅の最大値による正規化は下記の旧コードで確認した挙動。新実装での扱いは明記して検証する。正規化係数・適用範囲・診断値は下記の内部結果契約案で保持し、6係数ファイルへの追加や別ファイル保存の詳細は未確定。

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

ここに記載する値は旧コードのデフォルトであり、新実装の確定値ではない。

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

1. excitation-fitのNHF入力とrun単位の6係数JSON出力は確認済み。対数の底・振幅正規化の扱い、複数点NHFの場合の対象点選択は旧実装との差分を整理する。装置への設定操作は今回の対象外。
2. 最初に検証する代表的な入力ファイルと期待する結果。校正ファイル・測定ファイルの組と、係数計算用ファイルが必要。
3. 5つの接触モデルを最終的な移植対象として扱うか。初回の数値検証をHertzから始める案。
4. PiezoとCleanDriveの両方を必須とするか。校正値のファイル間差異や手動上書きの意図。

### 実装調査・数値検証で解決する事項

- 単位: 旧evaluate_specはforce*1e9を渡す一方、モデル側の1e9係数はコメントアウトされている。旧静的弾性率を無条件に正解としない。
- 校正: 旧コードは最初に読み込んだ校正値をグローバルに再使用する。m/Nチャネルの再校正方式も現convert_deflection_to_metersと異なる。
- 区間: find_frequency_changesの相対／絶対位置、先頭・終端と末尾2点除外の根拠。offsetフォールバックのN+1境界とN個の点数の整合性。
- 位相: 旧Sineのphi-1と現Sineのphi、ドリフト追加、位相unwrapと損失弾性率の符号への影響。
- Wait: 旧import_dataのwait_existsはローカル代入であり、後段には不在時もWaitを参照する箇所がある。
- 前処理: 旧VEAでは補正したindentationに対し、deflectionは元チャネルから取得している。復調対象の整合性を確認する。
- モデル: E_effという変数名と1/(1-nu**2)を含む式の意味、DMT gammaの定義・単位、DMT_Coneの係数を確認する。
- 周波数: 完全一致を初期仕様候補とする。共通周波数のみの解析・補間は別機能として明示する。
- 不正値: 欠損、短い区間、非正の押し込みDC、ゼロに近い複素分母、フィット失敗の扱いを定める。
- 座標: 旧／現コードの走査起点・XY反転の違いを非正方形マップで検証する。

## 8. この仕様整理の完了条件

- 2コマンドの必須入力、設定、出力、適用モデルが確定している。
- 旧挙動を維持する項目、修正する項目、後回しにする項目を区別できる。
- 代表入力と比較対象が決まり、物理量ごとに許容誤差を設定できる。
- コマンド登録とモデル登録の責務が合意され、GUIや新コマンドを追加しても計算を複製しない。
- 上記を満たしてからデータ契約・設定クラス・ワークフローの実装に進む。
