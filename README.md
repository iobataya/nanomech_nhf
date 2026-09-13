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
The VEA numerical analysis, performance optimization and GUI remain subsequent work.

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
points. Dynamic sample VEA analysis is not implemented yet. The shared selection retains the original map dimensions
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

Calibration and future sample VEA sine fits use `nm_models.FixedDriftSine`:
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

The current static model is Hertz sphere. Options (also config keys with underscores):
`--fit-direction Advance|Retract` (default Advance), `--tip-radius` (default 5e-9 m),
`--poisson-ratio` (default 0.5), `--baseline-start` (0.05) and `--baseline-end` (0.50).
The baseline is fitted against Z over the specified fraction of Advance samples
and subtracted from both directions. Force is in N, indentation in m and modulus
in Pa; fitting uses positive-force data with normalized parameters and residuals.
Static fitting delegates to `nm_models.HertzSphere.fit`, using its analytic
Jacobian and parameter scaling. Its optional `residual_scale` normalizes residuals
and Jacobians together (default 1 preserves other callers). The iteration limit,
contact bounds and physical output units are retained.

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
with known modulus pass recovery tests. Other contact models and dynamic sample
analysis remain subsequent work.

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
plotted; dynamic sample sine fitting remains subsequent work.

Calibration waveform plots can be saved during dry-run:

```powershell
python main.py vea --sample test-data-large/VEA-500-5k-sample.nhf --calibration test-data-large/VEA-500-5k-calibration.nhf --max_count 4 --dry-run --plot-calibration --output results
```

One PNG per frequency is saved to `results/<unique-run>/calibration/`, for example
`calibration_deflection_000_500Hz.png`. The plot overlays calibrated deflection
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
