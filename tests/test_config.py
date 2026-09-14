import argparse
from pathlib import Path

import pandas as pd
import pytest


@pytest.mark.parametrize('explicit', [False, True])
def test_excitation_toml_dispatch(tmp_path, monkeypatch, explicit):
    from dataclasses import make_dataclass
    from nanomech.cli import main
    result = make_dataclass('Result', [('coefficients', tuple)])((1, 2, 3, 4, 5, 6))
    seen = []
    def fit(path):
        seen.append(path)
        return result, {}
    monkeypatch.setattr('nanomech.workflows.excitation_fit', fit)
    path = tmp_path / 'excitation.toml'
    path.write_text('schema_version=1\ncommand="excitation-fit"\n[cli]\ninput="input.nhf"\noutput="out"\n')
    assert main((['excitation-fit'] if explicit else []) + ['--config', str(path)]) == 0
    assert seen == [tmp_path / 'input.nhf']
    assert len(list((tmp_path / 'out').glob('*/excitation_coefficients.json'))) == 1
    copied, = (tmp_path / 'out').glob('*/input_config.toml')
    assert copied.read_bytes() == path.read_bytes()


@pytest.mark.parametrize('content', ['schema_version=1', 'command="unknown"', 'command=["vea"]', 'broken=['])
def test_invalid_dispatch(tmp_path, content):
    from nanomech.cli import main
    path = tmp_path / 'invalid.toml'
    path.write_text(content)
    assert main(['--config', str(path)]) == 1


def test_command_mismatch(tmp_path):
    from nanomech.cli import main
    path = tmp_path / 'mismatch.toml'
    path.write_text('schema_version=1\ncommand="vea"')
    assert main(['excitation-fit', '--config', str(path)]) == 1

from nanomech.config import apply_vea_config
from nanomech.vea_command import configure_parser


def parse(path, extra=()):
    parser = argparse.ArgumentParser()
    parser.add_argument('--log-level', type=str.upper, choices=['INFO', 'DEBUG'])
    configure_parser(parser)
    args = parser.parse_args(['--config', str(path), *extra])
    apply_vea_config(args, parser)
    return args


def test_sections_precedence_and_paths(tmp_path):
    path = tmp_path / 'settings.toml'
    path.write_text('''schema_version=1
command="vea"
[cli]
sample="sample.nhf"
calibration="cal.nhf"
output="out"
max_count=4
plot_sample=true
log_level="debug"
[probe]
tip_radius=1e-8
sensitivity=1e-7
[static]
model="DMT_sphere"
fit_direction="retract"
''')
    args = parse(path, ['--max-count', '2', '--no-plot-sample'])
    assert args.max_count == 2
    assert args.plot_sample is False
    assert args.sample == tmp_path / 'sample.nhf'
    assert args.calibration == tmp_path / 'cal.nhf'
    assert args.output == tmp_path / 'out'
    assert args.model == 'DMT_Sphere'
    assert args.fit_direction == 'Retract'
    assert args.log_level == 'DEBUG'
    assert args.sensitivity is None
    assert args.file_config['sensitivity'] == 1e-7


@pytest.mark.parametrize('setting', ['max_count=true', 'plot_sample="false"',
    'max_count=1.5', 'unknown=3', 'excitation="invalid"',
    'max_count=1\nmax_points=2'])
def test_invalid_settings(tmp_path, setting):
    path = tmp_path / 'bad.toml'
    path.write_text('schema_version=1\ncommand="vea"\n[cli]\n' + setting)
    with pytest.raises(ValueError):
        parse(path)


def test_toml_analysis_and_output(tmp_path, monkeypatch):
    from nanomech import calibration
    from nanomech.cli import main
    root = Path(__file__).resolve().parents[1]
    sample = root / 'test-data-large/VEA-500-5k-sample.nhf'
    cal = root / 'test-data-large/VEA-500-5k-calibration.nhf'
    if not sample.exists() or not cal.exists():
        pytest.skip('Local VEA data unavailable')
    monkeypatch.setattr(calibration, 'SCRIPT_DIRECTORY', tmp_path)
    path = tmp_path / 'run.toml'
    path.write_text(f'''schema_version=1
command="vea"
[cli]
sample="{sample.as_posix()}"
calibration="{cal.as_posix()}"
output="out"
max_count=1
plot_sample=true
plot_calibration=true
max_plot_sample=1
[probe]
tip_radius=5e-9
poisson_ratio=0.5
[static]
model="DMT_Sphere"
fit_direction="advance"
''')
    assert main(['--config', str(path)]) == 0
    run, = (tmp_path / 'out').iterdir()
    assert (run / 'input_config.toml').read_bytes() == path.read_bytes()
    table = pd.read_csv(run / 'static_results.csv')
    assert table.model.iloc[0] == 'DMT_Sphere'
    assert table.young_modulus_pa.iloc[0] > 0
    assert (run / 'vea_results.csv').exists()
    gwy, = run.glob('*.gwy')
    assert gwy.read_bytes()[:4] == b'GWYP'
    assert (run / 'vea_fit_results.csv').exists()
    assert (run / 'calibration/calibration_deflection.png').exists()
    assert len(list((run / 'sample').glob('*.png'))) == 2
