# パフォーマンス計測

## 点位置メタデータのキャッシュ

`load_nhf_file()` で読み込んだmeasurementは、offset・datapointsを初回取得時に
キャッシュします。専用チャネルがある場合はセグメント単位、block-size方式は
セグメントと `dataset_block_size_source` の組み合わせ単位で再利用します。
ファイルの再読み込みでは新しいキャッシュを作成します。
返却配列は読み取り専用です。変更する場合は `.copy()` を使用してください。
読み込み後の境界メタデータ変更には追従しないため、変更後は再読み込みしてください。
`get_offset_datapoints()` の呼び出し回数は残りますが、再取得・再計算を省きます。

## 計測の概要

Python標準のcProfileで関数の呼び出し回数と処理時間を収集します。
追加依存は不要です。通常のCLI・GUI実行では計測しません。

## CLIの計測

リポジトリのルートで実行します。

```powershell
conda activate nanosurf
python -m nanomech.profiling --output profiles -- vea --sample test-data-large/VEA-500-5k-sample.nhf --calibration test-data-large/VEA-500-5k-calibration.nhf --max-count 4 --output results
python -m nanomech.profiling --output profiles -- --config examples/vea.toml
python -m nanomech.profiling --output profiles -- excitation-fit --input sample.nhf --output results
```

最初の `--output` は計測結果の親フォルダ、`--` より後は通常のCLI引数です。
解析・保存は通常どおり実行されます。終了コードも元のCLIと同じです。
実行ごとに日時と一意な接尾辞を持つフォルダを作り、その場所を表示します。
`profiles/` はGit管理対象外です。

| ファイル | 内容 |
|---|---|
| `summary.txt` | 全体の経過秒数と、累積時間・自身の時間・呼び出し回数別の上位50関数 |
| `functions.csv` | 全関数のファイル名・行番号・呼び出し回数・処理秒数。Excelで開けるUTF-8 BOM付き |
| `profile.pstats` | 呼び出し元・呼び出し先を含むcProfileの詳細データ |
| `run.json` | UTC開始日時、経過秒数、Python・OS、作業フォルダ、CLI引数と終了コード |

`total_calls` は再帰を含む回数、`primitive_calls` は再帰による呼び出しを除いた回数です。
`self_seconds`（summaryではtottime）は子関数を除く時間、
`cumulative_seconds`（cumtime）は子関数を含む時間です。
累積時間は関数間で重複するため、列を合計して全体時間にはできません。
まずcumtimeで重い処理の入口を探し、tottimeと回数で内訳を確認します。

詳細を対話的に調べる場合:

```powershell
python -m pstats profiles/<実行フォルダ>/profile.pstats
```

そのプロンプトで `sort cumulative`、`stats 30`、`callers analyze_static`、
`callees analyze_static` などを実行できます。

## 共通API・GUIワーカー内の計測

解析だけを対象にする場合は、依存モジュールのimport後にAPI呼び出しを囲みます。

```python
from nanomech.profiling import profile_run
from nanomech.workflows import run_vea

# requestは既存のVeaRequest
with profile_run("profiles", metadata={"case": "vea-4-points"}) as report_dir:
    result = run_vea(request)
print(report_dir)
```

計測対象はwithを実行しているスレッドです。GUIでは解析ワーカー内で
`run_vea` / `run_excitation_fit` を囲んでください。GUIの起動だけを囲んでも
バックグラウンド解析は計測されません。入れ子の計測は避けてください。

## 比較条件

- 同じ入力・点数・解析条件・PNG出力・ログレベルで比較してください。
- 校正ファイルを明示し、キャッシュ条件を揃えてください。
- 初回と2回目以降ではimportやOSのファイルキャッシュが異なります。
  同じ条件を数回実行し、初回を分けて経過時間の中央値などで比較してください。
- CLI用コマンドはCLIのimport・入力読み込み・解析・保存を含みます。
  レポート書き出し時間は計測に含めません。
- 計測自体に負荷があるため、秒数は通常実行より増えます。
  最終的な高速化は計測なしの実行時間でも確認してください。
- NumPyなどのネイティブ処理は呼び出し単位で見えますが、内部の処理や
  別スレッド・別プロセスの内訳は対象外です。メモリ使用量は計測しません。

例外発生時も、その時点までのレポートを保存して例外を呼び出し元に返します。
`run.json` のstatusはwith区間が例外なく終了したかを表します。
CLIがエラーを終了コードに変換した場合は、metadataのexit_codeで成否を確認してください。
