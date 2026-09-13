import json
from pathlib import Path

import numpy as np
import pytest

from nanomech.excitation import fit_excitation, polynomial, demodulate_amplitudes
from nanomech.cli import main


def test_polynomial_reconstruction():
    f = np.logspace(1, 4, 50)
    a = polynomial(f, 1., .2, .03, .004, .0005, .00006)
    result = fit_excitation(f, a)
    np.testing.assert_allclose(polynomial(f, *result.coefficients), a/a.max(), atol=1e-7)


@pytest.mark.parametrize("f,a", [([1]*6, [1]*6), ([0,1,2,3,4,5], [1]*6),
    (range(1,7), [0]*6), (range(1,7), [1,1,1,1,1,np.nan]), (range(1,6), [1]*5)])
def test_invalid_data(f, a):
    with pytest.raises(ValueError):
        fit_excitation(f, a)


def test_sine_amplitude():
    t = np.linspace(0, .1, 1000)
    y = .7 * np.sin(2*np.pi*100*t + .6) + .2
    np.testing.assert_allclose(demodulate_amplitudes(t,y,[100],[0,len(t)]), [.7], rtol=1e-6)


def test_missing_input(tmp_path):
    assert main(["excitation-fit", "--input", str(tmp_path/"absent.nhf"), "--output", str(tmp_path/"out")]) == 1
    assert not (tmp_path/"out").exists()


def test_config_validation(tmp_path):
    config = tmp_path/"config.json"
    config.write_text(json.dumps({"schema_version": 1, "command": "vea"}))
    assert main(["excitation-fit", "--config", str(config)]) == 1


def test_cli_overrides_config(tmp_path):
    source = Path(__file__).resolve().parents[1]/"test-data-large/VEA-power-corr.nhf"
    if not source.exists():
        pytest.skip("Local representative NHF is unavailable")
    config = tmp_path/"config.json"
    config.write_text(json.dumps({"schema_version": 1, "command": "excitation-fit",
                                 "input": "missing.nhf", "output": str(tmp_path/"out")}))
    assert main(["excitation-fit", "--config", str(config), "--input", str(source)]) == 0
    assert len(list((tmp_path/"out").glob("*/excitation_coefficients.json"))) == 1


def test_representative_legacy_comparison(tmp_path):
    source = Path(__file__).resolve().parents[1]/"test-data-large/VEA-power-corr.nhf"
    if not source.exists():
        pytest.skip("Local representative NHF is unavailable")
    for _ in range(2):
        assert main(["excitation-fit", "--input", str(source), "--output", str(tmp_path)]) == 0
    files = list(tmp_path.glob("*/excitation_coefficients.json"))
    assert len(files) == 2
    reference = [-1.33556678e3, 2.21279390e3, -1.45545461e3, 4.75199782e2, -7.70015254e1, 4.95339019]
    for file in files:
        values = json.loads(file.read_text())
        assert set(values) == {f"c{i}" for i in range(6)}
        np.testing.assert_allclose([values[f"c{i}"] for i in range(6)], reference, rtol=.01, atol=0)
