import os
import sys
import numpy as np

# Ensure repository root is on sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nm_gwy import NmGwyContainer, GwySizeInfo

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'results')
def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def test_nm_gwy_container():
    ensure_output_dir()
    # Create a NmGwyContainer with 2 channels, 3 rows, and 4 columns
    size_info = GwySizeInfo(x_offset=5.0e-6, y_offset=10.0e-6, x_range=1.0e-6, y_range=1.0e-6, unit_xy='m')
    container = NmGwyContainer(channel_size=2, y_size=3, x_size=4, physSizeInfo=size_info)

    # Set some values in the container
    container.set_result(0, 0, 0, 1.0)
    container.set_result(0, 1, 2, 2.5)
    container.set_result(1, 2, 3, 3.5)

    # Convert to list and check values
    result_list = container.to_list()
    assert len(result_list) == 2
    assert result_list[0][0, 0] == 1.0
    assert result_list[0][1, 2] == 2.5
    assert result_list[1][2, 3] == 3.5
    assert result_list[0][0,1] == 0.0  # Unset values should be zero
    assert result_list[1][0,0] == 0.0  # Unset values should be zero

    # Save as GWY file (this will create a file in the OUTPUT_DIR)
    gwy_path = os.path.join(OUTPUT_DIR, 'test_output.gwy')
    if os.path.exists(gwy_path):
        os.remove(gwy_path)

    data_labels = ['Channel 1', 'Channel 2']
    data_units = ['N', 'N']
    saved_path = container.save_as_gwy(gwy_path, data_labels=data_labels, data_units=data_units)
    
    # Check that the file was created
    assert os.path.exists(saved_path)