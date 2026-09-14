# nanomech_nhf
Nanomechanical analysis from NHF file obtained Nanosurf AFM

## Excitation coefficient CLI

Run in the `nanosurf` conda environment:

```powershell
conda run -n nanosurf python main.py excitation-fit --input test-data-large/VEA-power-corr.nhf --output results
```

The first measurement's point zero is fitted without opening a GUI. Each run
creates a new directory containing `excitation_coefficients.json` (c0 through c5)
and `run.json` (input, units, calibration scale and fit diagnostics).
The polynomial is `sum(ci * log10(frequency_Hz)**i)` for amplitude/max(amplitude).

An optional `--config config.json` accepts `schema_version: 1`,
`command: "excitation-fit"`, `input` and `output`. Explicit CLI values take
precedence. Relative paths are resolved from the current working directory.

```powershell
conda run --no-capture-output -n nanosurf python -m pytest tests/test_excitation.py -q
```

Local NHF comparison tests explicitly skip when the representative input is absent.
Additional contact models, performance optimization and GUI remain subsequent work.

## VEA point selection preview

```powershell
conda run --no-capture-output -n nanosurf python main.py vea --sample test-data-large/VEA-500-5k-sample.nhf --calibration test-data-large/VEA-500-5k-calibration.nhf --max_count 4 --crop_area "0,0:1,1" --dry-run
```

`--max_count` limits the number of attempted sample points. `--crop_area`
selects an inclusive rectangle in zero-based XY indices with the origin at the
bottom left. Crop is applied first, then the limit in original acquisition order.
Omitting both selects all points. Invalid or out-of-bounds selections fail.
`--max-count`, `--max_points`, `--max-points` and `--crop-area` are aliases.

Dry-run reads sample metadata, resolves probe calibration constants, and fits
calibration point zero. It does not load sample waveforms or calculate sample
material properties. It logs the selected count and up to 20 point indices/XY
positions. Without `--dry-run`, static Hertz analysis runs on selected sample
points, followed by per-frequency sample VEA sine fits and Hertz dynamic moduli.
The shared selection retains the original map dimensions
for future full-size result output.

`--config` accepts JSON with `schema_version: 1`, `command: "vea"`, `sample`,
`max_count` and `crop_area`. Explicit CLI options override config values.
The old config name `max_points` is accepted, but cannot coexist with `max_count`.

VEA calibration selection (also applied during `--dry-run`):

- `--calibration path.nhf` always opens that file. After successful metadata
  validation it is copied to `.last_calibration.nhf` beside `main.py`.
- Without `--calibration`, that cached file is opened, regardless of the current
  working directory. The cache contains the NHF itself, not a path reference.
- Missing or invalid explicit input raises an error without falling back to the
  cache. Missing/invalid cache also fails. The CLI returns exit code 1.

DEBUG logs record the selected absolute path and whether it came from CLI or
cache. Cache replacement is atomic and preserves the previous file if copying
fails. These temporary files are excluded from Git. Dry-run validates metadata,
updates the cache, and performs calibration sine fits as preparation for analysis.

`--sensitivity` (m/V) and `--spring_constant` / `--spring-constant` (N/m)
override config `sensitivity` and `spring_constant`. Each constant independently
falls back to the sample measurement attribute, then the calibration measurement
attribute. Missing constants and nonpositive/nonfinite values fail. Adopted values,
units and origins are logged. Saved displacement/force channels use their original
file calibration to recover detector volts before applying the new sensitivity;
force is displacement times the adopted spring constant.

Calibration fits use point zero, the central 40% of each frequency segment and
the legacy sine phase convention `sin(2*pi*f*t + phase - 1)`. INFO logs report
amplitude, fitted frequency, phase, DC and residual norm for Deflection,
Indentation and Position Z at each frequency. Phase is unwrapped across the sweep.
Calibration/sample sweep mismatches and calibration fit failures abort preparation.

Calibration and future sample VEA sine fits use `nanomech.nm_models.FixedDriftSine`:
drift is exactly zero, and residuals plus analytic Jacobians are normalized by
the segment half peak-to-peak amplitude. Parameter scaling is also applied.
Zero-amplitude segments fail rather than dividing by zero. Returned phases retain
the legacy convention and logged residual norms retain physical signal units.
The separate legacy-compatible excitation-fit demodulation remains unchanged.

```powershell
python main.py vea --sample test-data-large/VEA-500-5k-sample.nhf --calibration test-data-large/VEA-500-5k-calibration.nhf --sensitivity 4.438e-8 --spring_constant 0.08405063054669279 --max_count 4 --dry-run
```

## Static Young's modulus analysis

```powershell
python main.py vea --sample test-data-large/VEA-500-5k-sample.nhf --calibration test-data-large/VEA-500-5k-calibration.nhf --max_count 4 --crop_area "0,0:1,1" --output results
```

Static models are `Hertz` (default), `Sneddon`, `Pyramid`, `DMT_Sphere`, and
`DMT_Cone`. Select with `--model`; names are case-insensitive, so `DMT_sphere`
is accepted. `StaticConfig.model` and config JSON use the same names.
Options (also config keys with underscores):
`--fit-direction Advance|Retract` (default Advance), `--tip-radius` (default 5e-9 m),
`--poisson-ratio` (default 0.5), `--baseline-start` (0.05) and `--baseline-end` (0.50).
`--cone-half-angle` / `cone_half_angle` is the cone/pyramid half angle in degrees
(default 15, strictly between 0 and 90). Sphere models use tip radius.
The baseline is fitted against Z over the specified fraction of Advance samples
and subtracted from both directions. Force is in N, indentation in m and modulus
in Pa; fitting uses positive-force data with normalized parameters and residuals.
Static fitting delegates to `nanomech.nm_models.HertzSphere.fit`, using its analytic
Jacobian and parameter scaling. Its optional `residual_scale` normalizes residuals
and Jacobians together (default 1 preserves other callers). The iteration limit,
contact bounds and physical output units are retained.

All five contact equations are implemented in `nm_models` with analytic Jacobians,
parameter scaling and normalized residuals. DMT fits also estimate `gamma`, saved
as `adhesion_parameter_n_per_m` in both result tables (zero for nonadhesive models).
Under the implemented equations gamma has units N/m; this does not establish a
physical interpretation of the legacy DMT_Cone adhesion parameter.
For DMT, full-curve residuals and multiple initial contact positions are used.
Unlike legacy `ignore_baseline=True`, points are not dropped dynamically when
the contact estimate moves. This prevents a spuriously low residual from omitting
data. Nonadhesive models continue using positive-force samples.

Model selection also controls static plot names/curves and the legacy dynamic
geometry factors (sphere for Hertz/DMT_Sphere, cone for Sneddon/DMT_Cone, pyramid
for Pyramid). Existing legacy-comparison limitations still apply.

```powershell
python main.py vea --sample test-data-large/VEA-500-5k-sample.nhf --model DMT_sphere --max_count 4 --plot-sample
```

Each run writes `static_results.csv` via pandas, with one row per original point,
and `run.json` with resolved settings, probe provenance and overall status. CSV
contains point index, XY, direction, model, Young's modulus, contact position,
residual norm, snap-in/adhesion force, baseline coefficients, status and failure
reason. Unselected points retain zero results and `unprocessed`; failed points
contain `NaN` and `failed`. All selected points failing returns exit code 1 after
writing results. Partial success is recorded as `partial_failure`.

The representative point-zero result is approximately 2.313 MPa, differing from
the legacy CSV's 0.100 MPa beyond the agreed 1% tolerance. This comparison has
not passed. The legacy fitter mixes nN input with an SI model; the new fitter
uses consistent units and numerical scaling. Synthetic Advance/Retract curves
with known modulus pass recovery tests. Other contact models remain subsequent work.

## Calibration plots and logging

For static sample overlays, add `--plot-sample`. Use `--max-plot-sample 2` to
save at most two successful sample plots in acquisition order; omitting the limit
plots all successfully fitted selected points. Zero saves no sample plots and
negative values are rejected. The limit affects only plotting, not analysis or
CSV rows. Without `--plot-sample`, the limit alone does not enable plotting.

```powershell
python main.py vea --sample test-data-large/VEA-500-5k-sample.nhf --max_count 4 --plot-sample --max-plot-sample 2 --output results
```

Sample PNGs go to `results/<run>/sample/`, for example
`sample_point00000_Hertz_advance.png`. Each shows the fitted direction's
baseline-corrected force (nN) versus indentation (nm), the existing fitted curve,
Young's modulus, contact position, residual norm, radius and Poisson ratio.
The indentation coordinate retains its contact offset, matching the fitted data.
No waveform reread or refit is performed for plotting. Failed/unprocessed points
have no fitted plot and do not consume the plot limit. `--dry-run` skips sample
analysis and sample plots. Currently only the implemented static Hertz model is
plotted for static analysis. The same option also saves dynamic deflection versus
time with fitted sine curves, stacking all frequencies vertically in one image
per point, matching the calibration layout. Failed deflection fits are labeled.
`--max-plot-sample` applies independently to static and dynamic point images;
it does not limit the number of frequency panels or analysis points.

Both outputs use the shared naming rule
`sample_point{index}_{model}_{segment}.png`, for example
`sample_point00000_Hertz_advance.png` and `sample_point00000_sine_VEA.png`.
Index width is `len(str(measurement_total_count))`, regardless of crop/count
selection. `plot_static_sample(..., index_digits=5)` retains five digits as the
API default; the CLI passes the computed width to both plotters. No frequency
is included in a sample filename. Plotting reuses the fitted data and does not
reload or refit the waveforms.

## Sample VEA sine fitting

Normal `vea` execution now runs static fitting and then VEA fitting for each
successful selected point. The command and selection options are unchanged.
`--dry-run` still stops after calibration preparation.

`vea_fit_results.csv` is written via pandas with one row per original point and
nominal sweep frequency. Columns include point index, XY, frequency/index,
static/VEA/channel status, failure reason, and each channel's amplitude (m), fitted
frequency (Hz), phase (rad), DC (m), and residual norm (m). Channels are deflection,
indentation and position_z. Rows retain acquisition order, then sweep order.

Deflection receives resolved sensitivity and the static linear baseline
correction; indentation is `-(Z + corrected_deflection) - contact_point`.
Position Z retains its calibrated waveform. Fits use `FixedDriftSine`, normalized
residuals/Jacobians and the central 40%, with the same phase convention as
calibration. Phase is unwrapped within consecutive successful frequency fits;
an error resets unwrapping for that channel. Point-local raw slices prevent
loading the entire sample waveform. Sweep boundaries retain the calibration's
legacy metadata convention.

Unselected rows have zero results and `unprocessed`. Static failures produce NaN
and `skipped_static_failed`. A failed frequency/channel records NaN and a reason;
successful channels and later frequencies are preserved. `run.json` records both
static and dynamic status. No fully successful frequency row returns exit code 1;
mixed success records `partial_failure`. Reference-channel fitting is not included.

## Elastic modulus tables

Normal `vea` execution also writes `vea_results.csv`: one row per original point
and frequency containing the fit diagnostics, static Young's modulus/contact data,
`storage_modulus_pa`, `loss_modulus_pa`, `loss_tangent`, `modulus_status` and
`modulus_failure_reason`. `static_results.csv` remains one row per point;
`vea_fit_results.csv` retains the intermediate sine fits. All CSV files are
written through pandas without its index; failed values use `NaN`, while
unselected results remain zero with `unprocessed` status.

`--excitation auto|Piezo|CleanDrive` defaults to auto. Auto follows the legacy
sample sweep `output_id` rule (1 means CleanDrive; otherwise Piezo).
`--no-correct-drag` disables the default Piezo drag correction. Config keys are
`excitation` and `correct_drag`, overridden by CLI values. CleanDrive uses the
calibration/sample deflection ratio, without applying Piezo drag correction.

For Hertz, with fitted complex deflection D, indentation I and sample indentation
DC d, `B=(1-nu)*k/(4*sqrt(R)*sqrt(d))`. Piezo uses
`Q=Ds/Is-Dr/Ir` (omit the last term when drag correction is disabled); CleanDrive
uses `Q=Dr/Ds-1`. `E*=2*(1+nu)*B*Q`. Real/imaginary parts give storage/loss modulus;
their ratio gives loss tangent. These are the recorded legacy equations.
Nonpositive indentation DC and negligible denominators fail explicitly. The
relative denominator guard is 1e-12 of the corresponding response amplitude
scale. Undefined tangent preserves finite storage/loss values but records partial
failure. No reference-channel phase correction is applied (`use_reference=false`).

Representative point 0 at 500 Hz (CleanDrive): storage approximately 4.151 MPa,
loss 0.231 MPa, tan(delta) 0.05566. These do not pass the 1% comparison with legacy
CSV values (1.443 MPa / 0.08061 MPa). Static contact and preprocessing changes
affect these results; the discrepancy remains unresolved. Independent tests recover
known complex moduli for both excitation formulas.

Calibration waveform plots can be saved during dry-run:

```powershell
python main.py vea --sample test-data-large/VEA-500-5k-sample.nhf --calibration test-data-large/VEA-500-5k-calibration.nhf --max_count 4 --dry-run --plot-calibration --output results
```

All frequencies are stacked vertically in sweep order in one PNG:
`results/<unique-run>/calibration/calibration_deflection.png`. Each subplot is
labeled with its frequency; the filename contains no frequency. The plot overlays calibrated deflection
(nm) against time from segment start (ms) with the existing sine fit, and shades
the central 40% fitting interval. Plotting does not refit or open a GUI window.
Without `--plot-calibration`, no plots are created. `--output` overrides config
`output`; the default is `results`. Each run gets a new directory.

Use `--log-level DEBUG` (alias `--log_level`) before or after the command name.
Levels are `DEBUG`, `INFO` (default), `WARNING`, `ERROR`, and `CRITICAL`;
lowercase names are also accepted. DEBUG logs show the effective VEA `crop_area`
and `max_count` after config/CLI resolution. Each unspecified value is shown as `ALL`.

```powershell
python main.py vea --sample test-data-large/VEA-500-5k-sample.nhf --dry-run --log-level DEBUG
```
# TOMLによるVEA解析設定

通常のVEA解析ではCSVと同じ出力ディレクトリに `<sample名>_VEAnalysis.gwy` を自動保存します。
追加のオプションは不要です（`--dry-run` では保存しません）。
静的結果5チャンネル（接触位置、ヤング率、DMT Gamma、snap-in力、付着力）と、
周波数ごとの貯蔵弾性率・損失弾性率・tan δを保存します。5周波数なら合計20チャンネルです。
単位はそれぞれ m、Pa、N/m、N、N、Pa、Pa、無次元です。
CSVと同じ値を使用し、未処理点は0、失敗値はNaNとGWYマスクで保持します。
cropや点数制限を指定しても元のマップサイズを維持します。詳細な状態と失敗理由はCSVを参照してください。
NHFのX/Y範囲とscanner offsetを同名のGWY軸に設定し、蛇行走査をXY座標へ復元して
上下反転したラスタを保存します。軸の入れ替えは行いません。
scanner rotationはメタデータに記録し、画像の回転・補間は行いません。

VEAのcalibrationはdeflection波形から周波数を推定し、NHF設定から生成した周波数との
相対誤差 `abs(f_fit - f_NHF) / f_NHF` が5%を超えるとエラーで停止します。
推定時の探索範囲は設定周波数の0.5〜1.5倍で、推定周波数・誤差をINFOログに出力します。
検証後のcalibration全チャンネルとsampleはNHF周波数を固定して再フィットします。
ドリフトは0、残差は正規化し、固定周波数のsin・cos・DC係数を線形最小二乗で求めます。
この検証とcalibrationの固定周波数フィットは `--dry-run` でも実行します。
CSVの `*_fitted_frequency_hz` は最終フィットに使用したNHF周波数になります。

設定例は [`examples/vea.toml`](examples/vea.toml) を参照してください。
入力ファイルのパスを編集し、次のコマンドで解析からCSV・PNG出力まで実行できます。

```powershell
python main.py --config examples/vea.toml
```

サブコマンドを省略するとTOML内の `command`（`vea` または `excitation-fit`）を使用します。
従来の `python main.py vea --config ...` も利用できますが、明示したコマンドと設定ファイルの `command` は一致する必要があります。
`excitation-fit` のTOMLは `schema_version = 1`、`command = "excitation-fit"` と、
`[cli]` 内の `input`・`output`・任意の `log_level` で指定できます。

TOMLは `schema_version = 1` と `command = "vea"` を必須とし、以下のテーブルを使用します。

| テーブル | 設定 |
|---|---|
| `[cli]` | `sample`, `calibration`, `output`, `max_count`, `crop_area`, `log_level`, `dry_run`, `plot_calibration`, `plot_sample`, `max_plot_sample`, `excitation`, `correct_drag` |
| `[probe]` | `tip_radius`（m）, `cone_half_angle`（度）, `poisson_ratio`, `sensitivity`（m/V）, `spring_constant`（N/m） |
| `[static]` | `fit_direction`（advance/retract）, `model`（Hertz/Sneddon/Pyramid/DMT_Sphere/DMT_Cone）, `baseline_start`, `baseline_end` |

優先順位は **明示したCLI引数 → 設定ファイル → 既定値** です。
感度・ばね定数が未指定なら従来どおりNHFのメタデータから取得します。
calibrationが未指定なら従来の `.last_calibration.nhf` を使用します。
TOML内の相対パスはTOMLファイルのあるディレクトリが基準です。
Windowsパスには `/` またはTOMLのシングルクォート文字列を使用してください。
未指定の `max_count` / `crop_area` は全点対象です。出力先には実行ごとのサブディレクトリを作成します。

CLIで一部だけ上書きする例：

```powershell
python main.py --config examples/vea.toml --model DMT_sphere --fit-direction retract --max-count 4 --log-level DEBUG
python main.py --config examples/vea.toml --no-plot-sample --no-plot-calibration
```

従来のJSON設定も使用できます（JSONの相対パスは従来どおり作業ディレクトリ基準）。
不明なキー、設定の重複、型や選択肢の誤りは解析前にエラーになります。
