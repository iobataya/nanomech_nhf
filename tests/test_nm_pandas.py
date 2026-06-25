import os
import sys
import numpy as np
import pandas as pd

# Ensure repository root is on sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nm_pandas import FieldMap, FieldSweepTable

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'results')

def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)



def test_init_field_map():
    ensure_output_dir()
    xy_point_count = 25
    parameters = ["Force", "Indentation", "Modulus"]
    field_map = FieldMap(xy_point_count, parameters)

    assert field_map.xy_point_count == xy_point_count
    assert field_map.parameters == parameters
    assert list(field_map.table.columns) == ["Point index"] + parameters
    assert field_map.table.shape == (0, len(parameters) + 1)  # No rows yet


def test_set_parameters_at():
    ensure_output_dir()
    xy_point_count = 25
    parameters = ["Force", "Indentation", "Modulus"]
    field_map = FieldMap(xy_point_count, parameters)

    # Set parameters at point index 5
    point_index = 5
    param_values = {"Force": 1.0, "Indentation": 0.5, "Modulus": 200.0}
    field_map.set_parameters_at(point_index, param_values)

    # Verify the values are set correctly
    row = field_map.table[field_map.table["Point index"] == point_index]
    assert not row.empty
    assert row.iloc[0]["Force"] == 1.0
    assert row.iloc[0]["Indentation"] == 0.5
    assert row.iloc[0]["Modulus"] == 200.0

def test_field_map_to_csv():
    ensure_output_dir()
    xy_point_count = 25
    parameters = ["Force", "Indentation", "Modulus"]
    field_map = FieldMap(xy_point_count, parameters)

    # Set some parameters at different point indices
    field_map.set_parameters_at(0, {"Force": 1.0, "Indentation": 0.5, "Modulus": 200.0})
    field_map.set_parameters_at(1, {"Force": 2.0, "Indentation": 1.0, "Modulus": 250.0})

    # Save to CSV
    csv_path = os.path.join(OUTPUT_DIR, "field_map_test.csv")
    field_map.to_csv(csv_path)

    # Verify the CSV file exists and has the correct
    assert os.path.exists(csv_path)
    loaded_df = pd.read_csv(csv_path)
    assert loaded_df.shape[0] == 2  # Two rows for two point indices
    assert list(loaded_df.columns) == ["Point index"] + parameters

def test_field_sweep_table():
    ensure_output_dir()
    xy_point_count = 25
    parameters = ["Force", "Indentation", "Modulus"]
    sweep_table = FieldSweepTable(xy_point_count, parameters)

    # Set swept parameters at point index 0
    point_index = 0
    sweeping_param_name = "Frequency"
    params_array = {
        "Frequency": [100, 200, 300],
        "Force": [1.0, 2.0, 3.0],
        "Indentation": [0.5, 1.0, 1.5],
        "Modulus": [200.0, 250.0, 300.0]
    }
    sweep_table.set_swept_parameters_at(point_index, sweeping_param_name, params_array)

    # Verify the values are set correctly
    rows = sweep_table.table[sweep_table.table["Point index"] == point_index]
    assert not rows.empty
    assert len(rows) == len(params_array["Frequency"])  # Should have one row per frequency value

def test_field_sweep_table_to_csv():
    ensure_output_dir()
    xy_point_count = 25
    parameters = ["Force", "Indentation", "Modulus"]
    sweep_table = FieldSweepTable(xy_point_count, parameters)

    # Set swept parameters at point index 0
    point_index = 0
    sweeping_param_name = "Frequency"
    params_array = {
        "Frequency": [100, 200, 300],
        "Force": [1.0, 2.0, 3.0],
        "Indentation": [0.5, 1.0, 1.5],
        "Modulus": [200.0, 250.0, 300.0]
    }
    sweep_table.set_swept_parameters_at(point_index, sweeping_param_name, params_array)

    # Save to CSV
    csv_path = os.path.join(OUTPUT_DIR, "field_sweep_table_test.csv")
    sweep_table.table.to_csv(csv_path, index=False)

    # Verify the CSV file exists and has the correct number of rows
    assert os.path.exists(csv_path)
    loaded_df = pd.read_csv(csv_path)
    assert loaded_df.shape[0] == len(params_array["Frequency"])  # Should have one row per frequency value