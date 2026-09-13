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
conda run --no-capture-output -n nanosurf python main.py vea --sample test-data-large/VEA-500-5k-sample.nhf --max_count 4 --crop_area "0,0:1,1" --dry-run
```

`--max_count` limits the number of attempted sample points. `--crop_area`
selects an inclusive rectangle in zero-based XY indices with the origin at the
bottom left. Crop is applied first, then the limit in original acquisition order.
Omitting both selects all points. Invalid or out-of-bounds selections fail.
`--max-count`, `--max_points`, `--max-points` and `--crop-area` are aliases.

This preview reads measurement metadata only, without loading waveform channels
or calculating material properties. It logs the selected count and up to 20 point
indices/XY positions. Numerical VEA analysis is not implemented yet; `--dry-run`
is currently required. The shared selection retains the original map dimensions
for future full-size result output.

`--config` accepts JSON with `schema_version: 1`, `command: "vea"`, `sample`,
`max_count` and `crop_area`. Explicit CLI options override config values.
The old config name `max_points` is accepted, but cannot coexist with `max_count`.

## Logging

Use `--log-level DEBUG` (alias `--log_level`) before or after the command name.
Levels are `DEBUG`, `INFO` (default), `WARNING`, `ERROR`, and `CRITICAL`;
lowercase names are also accepted. DEBUG logs show the effective VEA `crop_area`
and `max_count` after config/CLI resolution. Each unspecified value is shown as `ALL`.

```powershell
python main.py vea --sample test-data-large/VEA-500-5k-sample.nhf --dry-run --log-level DEBUG
```
