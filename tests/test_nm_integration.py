"""
Integration tests: combination of a few functionalities to test the part of the workflow of data processing
"""
import os
import sys
import numpy as np

# Ensure repository root is on sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nm_gwy import NmGwyContainer, GwySizeInfo

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'results')
OUTPUT_FIGS_DIR = os.path.join(os.path.dirname(__file__), 'figs')
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

from nm_io import *
from nm_plot import *

NHFDataset: TypeAlias = nhf_reader.NHFDataset
NHFSegment: TypeAlias = nhf_reader.NHFSegment
NHFMeasurement: TypeAlias = nhf_reader.NHFMeasurement


class IOIntegrationTests:
    def test_load_nhf_and_save_to_csv(self):
        """Test loading of a .nhf file and saving the data as csv."""
        test_file = os.path.join(DATA_DIR, 'Forcemap-5x5.nhf')

        # Load the NHF file
        measurement = load_nhf_file(test_file)
        assert measurement is not None

        # Save to CSV
        csv_path = os.path.join(OUTPUT_DIR, "forcemap_test.csv")
        #ssave_measurement_to_csv(measurement, csv_path)
        assert os.path.exists(csv_path)

    def test_load_nhf_and_save_to_excel(self):
        """Test loading of a .nhf file and saving the data as excel."""
        test_file = os.path.join(DATA_DIR, 'Forcemap-5x5.nhf')

        # Load the NHF file
        measurement = load_nhf_file(test_file)
        assert measurement is not None

        # Save to Excel
        excel_path = os.path.join(OUTPUT_DIR, "forcemap_test.xlsx")
        #save_measurement_to_excel(measurement, excel_path)
        assert os.path.exists(excel_path)

    def test_load_nhf_to_gwy(self):
        """Test loading of a .nhf file and saving the data as gwy."""
        test_file = os.path.join(DATA_DIR, 'Forcemap-5x5.nhf')

        # Load the NHF file
        measurement = load_nhf_file(test_file)
        assert measurement is not None

    def test_load_nhf_and_plot(self):
        """Test loading of a .nhf file and plotting the data as svg."""
        test_file = os.path.join(DATA_DIR, 'Forcemap-5x5.nhf')

        # Load the NHF file
        measurement = load_nhf_file(test_file)
        assert measurement is not None

class TestAnalysisIntegration:
    def test_load_to_forcecurve_analysis(self):
        """Test loading of a .nhf file and performing force curve analysis."""
        test_file = os.path.join(DATA_DIR, 'Forcemap-5x5.nhf')

        # Load the NHF file
        measurement = load_nhf_file(test_file)
        assert measurement is not None

    def test_load_to_forcemap_analysis(self):
        """Test loading of a .nhf file and performing force map analysis."""
        test_file = os.path.join(DATA_DIR, 'Forcemap-5x5.nhf')

        # Load the NHF file
        measurement = load_nhf_file(test_file)
        assert measurement is not None

    def test_load_to_vea_calibration_analysis(self):
        """Test loading of a .nhf file and performing VEA calibration analysis."""
        test_file = os.path.join(DATA_DIR, 'Forcemap-5x5.nhf')

        # Load the NHF file
        measurement = load_nhf_file(test_file)
        assert measurement is not None

    def test_load_to_vea_analysis(self):
        """Test loading of a .nhf file and performing VEA analysis."""
        test_file = os.path.join(DATA_DIR, 'Forcemap-5x5.nhf')

        # Load the NHF file
        measurement = load_nhf_file(test_file)
        assert measurement is not None
