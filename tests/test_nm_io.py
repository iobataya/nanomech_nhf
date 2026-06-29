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

class TestMethods:
    def test_load_nhf_single_forcecurve_file(self):
        """Test loading of a .nhf file."""
        test_file = os.path.join(DATA_DIR, 'ForceCurve-single.nhf')
        measurement = load_nhf_file(test_file)
        assert measurement is not None
        assert measurement.channel is not None
        logger.info(f"Channels ({type(measurement.channel)}) loaded: {list(measurement.channel.keys())}")
        assert measurement.segment is not None
        assert Segment.ADVANCE in measurement.segment
        assert Segment.RETRACT in measurement.segment
        logger.info(f"Segments ({type(measurement.segment)}) loaded: {list(measurement.segment.keys())}")
        advance_segment = measurement.segment[Segment.ADVANCE]
        logger.info(f"Advance segment channels: {list(advance_segment.channel.keys())}") 
        x = advance_segment.read_channel(Channel.Z_POSITION)
        y = advance_segment.read_channel(Channel.DEFLECTION)
        logger.info(f"Deflection channel ({type(y)}): {y.dataset.shape}")
        logger.info(f"Z Position channel ({type(x)}): {x.dataset.shape}")

        name = "test_nhf_forcespec.png"
        
        logger.debug(f"x {x.dataset[0:5], x.dataset[-5:]}, y {y.dataset[0:5], y.dataset[-5:]}")

        logger.debug(f"min(x,y) = {np.min(x.dataset)}, {np.min(y.dataset)}; max(x,y) = {np.max(x.dataset)}, {np.max(y.dataset)}")
        plot_data(x, [], [], y, [], [], 'ForceSpec', None, show_plot=False)
        path = os.path.join(OUTPUT_FIGS_DIR, name)
        plt.savefig(path)
        plt.close()
        assert os.path.exists(path)

        # TODO: チャンネルの最後尾にfloatの最小値が入っている。
        
