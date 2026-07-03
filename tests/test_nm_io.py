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
        time_ch = advance_segment.read_channel(Channel.TIME)
        logger.info(f"Deflection channel ({type(y)})")
        logger.info(f"Z Position channel ({type(x)})")

        name = "test_nhf_forcespec.png"
        
        #logger.debug(f"x {x.dataset[0:5], x.dataset[-5:]}, y {y.dataset[0:5], y.dataset[-5:]}")

        # dataset has minimum value of float64 at the end.
        # where do they start ? 
        abnormal_elements = np.where(x.dataset<-1e+308)
        logger.debug(f"abnormal : {abnormal_elements}")


        logger.debug(f"min(x,y) = {np.min(x.dataset)}, {np.min(y.dataset)}; max(x,y) = {np.max(x.dataset)}, {np.max(y.dataset)}")
        logger.debug(f"x from 1560 to 1570 {x.dataset[1560:1571]}")
        logger.debug(f"time from 1560 to 1570 {time_ch.dataset[1560:1571]}")

        # find unrealistic negative value -1.79769e+308
        # Reported CSM-726
        neg_in_x = np.where(x.dataset < -1e+308)[0].min()
        neg_in_y = np.where(y.dataset < -1e+308)[0].min()
        neg_in_time = np.where(time_ch.dataset < -1e+308)[0].min()
        logger.debug(f"neg_in_x = {neg_in_x}, neg_in_y = {neg_in_y}, neg_in_time = {neg_in_time}")

        # Mask the wrong values
        threshold = -1e+308
        x.dataset[x.dataset < threshold] = np.nan
        y.dataset[y.dataset < threshold] = np.nan
        time_ch.dataset[time_ch.dataset < threshold] = np.nan


        plt.scatter(x=x.dataset, y=y.dataset)
        path = os.path.join(OUTPUT_FIGS_DIR, name)
        plt.savefig(path)
        plt.close()
        assert os.path.exists(path)

        # TODO: チャンネルの最後尾にfloatの最小値が入っている。
