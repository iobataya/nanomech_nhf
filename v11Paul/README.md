# 旧コードの比較結果を生成するスクリプト

`demo_VEA_analysis_v11_evalCoeffsPolynom.py` を元に、計算関数・グローバル設定をそのまま複製し、実行入口のみ分離しています。元ファイルは変更していません。

## 励振係数計算

リポジトリのルートから実行:

```powershell
python v11Paul/legacy_excitation_fit.py --calibration test-data-large/VEA-power-corr.nhf
```

先頭measurementの点0を処理し、旧コードどおり係数・診断値を標準出力に表示します。標準出力とエラーをファイルへ保存し、描画を省略する場合:

```powershell
python v11Paul/legacy_excitation_fit.py --calibration test-data-large/VEA-power-corr.nhf --no-plots *> test-data-large/legacy-excitation-fit.txt
```

## VEA解析

```powershell
python v11Paul/legacy_vea.py --calibration test-data-large/VEA-500-5k-calibration.nhf --measurement test-data-large/VEA-500-5k-sample.nhf
```

係数計算は実行せず、calibrationとsampleを読み込んでsampleの全点を解析し、点別CSVとGWYを出力します。出力先はsampleと同じディレクトリ内に作る日時付きrunディレクトリです。

出力先を指定し、描画を省略する場合（指定先は未作成のディレクトリにしてください）:

```powershell
python v11Paul/legacy_vea.py --calibration test-data-large/VEA-500-5k-calibration.nhf --measurement test-data-large/VEA-500-5k-sample.nhf --output-dir test-data-large/legacy-vea-run-001 --no-plots *> test-data-large/legacy-vea-run-001.txt
```

## 比較時の注意

- これらは旧計算の比較用です。策定中の新仕様（JSON係数出力、校正値優先順位、max_points、crop_area、部分失敗の継続等）の実装ではありません。
- 旧コードと同じPython依存関係を使用します。`nanosurf.lib.util` からのimportも維持しています。
- モデル・先端形状・校正値等の設定は各スクリプト冒頭にあります。実行モードを変えるためのコメント編集は不要です。
- `--no-plots` は描画を省略します。旧evaluate_specは描画分岐内でも配列を更新するため、描画有無を含む実行条件を比較記録に残してください。
- 旧コードの単位スケーリング、区間検出、Wait不在処理等の既知の検証事項も維持しています。結果は旧実装の比較値として扱い、物理的な正解と無条件にみなさないでください。
- 旧eval_coeffs_funcは内部で一部のエラーを捕捉してTrueを返すため、終了コードだけでなく、係数6個とエラーメッセージの有無も確認してください。
- 構文検証と、計算関数・設定部分が元コードと同一であることを確認済みです。検証用Python環境にはnanosurfがないため、NHFを用いた実行検証は未実施です。
