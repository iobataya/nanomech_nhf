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
The VEA command, performance optimization and GUI remain subsequent work.
