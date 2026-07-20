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

class TestNHFReader:
    def test_load_nhf_file(self):
        """Test loading of a .nhf file."""
        test_file = os.path.join(DATA_DIR, 'Forcemap-5x5.nhf')

        nhf_file = nhf_reader.NHFFileReader(verbose=True)
        assert nhf_file.read(test_file)

        logger.info(str(nhf_file))

        

class TestMethods:
    def test_load_nhf_forcemapping(self):
        """Test loading of a .nhf file."""
        test_file = os.path.join(DATA_DIR, 'Forcemap-5x5.nhf')

        # NHFMeasurement is a dataclass with attributes: channel, segment, and metadata.
        measurement = load_nhf_file(test_file)
        assert measurement is not None
        nhf_summary = summary_nhf_measurement(
            measurement,
            show_channel=True,
            show_segment=True,
            show_attribute=True)
        logger.info(nhf_summary)

        assert measurement.channel is not None
        ch_coord_x = measurement.channel.get('coordinates_x')

        # measurement.segment is a dictionary with keys 'advance' and 'retract'
        assert measurement.segment is not None
        assert Segment.ADVANCE in measurement.segment
        assert Segment.RETRACT in measurement.segment

        # Force mapping
        # 
        

    def test_load_nhf_single_forcecurve_file(self):
        """Test loading of a .nhf file."""
        test_file = os.path.join(DATA_DIR, 'ForceCurve-single.nhf')

        # NHFMeasurement is a dataclass with attributes: channel, segment, and metadata.
        measurement = load_nhf_file(test_file)
        assert measurement is not None
        nhf_summary = summary_nhf_measurement(
            measurement,
            show_channel=True,
            show_segment=True,
            show_attribute=True)
        logger.info(nhf_summary)

        # measurement.segment is a dictionary with keys 'advance' and 'retract'
        assert measurement.segment is not None
        assert Segment.ADVANCE in measurement.segment
        assert Segment.RETRACT in measurement.segment

        # segment[Segment.ADVANCE] is a dictionary with keys of channels.
        advance_segment = measurement.segment[Segment.ADVANCE]
        x = advance_segment.read_channel(Channel.Z_POSITION)
        y = advance_segment.read_channel(Channel.DEFLECTION)
        meta = advance_segment.read_channel('Sampler Timestamp')
        time_ch = advance_segment.read_channel(Channel.TIME)
        
        #logger.debug(f"x {x.dataset[0:5], x.dataset[-5:]}, y {y.dataset[0:5], y.dataset[-5:]}")
        # dataset has minimum value of float64 at the end.
        # where do they start ? 
        abnormal_elements = np.where(x.dataset<-1e+308)
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

        name = "test_nhf_forcespec.png"
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()

        # Plot two parameters against the same x-axis with separate y-axes.
        p1 = ax1.scatter(x.dataset, y.dataset, s=8, color='blue', label='Deflection')
        p2 = ax2.scatter(x.dataset, meta.dataset, s=8, color='red', label='Sampler Meta')

        ax1.set_xlabel('Z Position')
        ax1.set_ylabel('Deflection', color='blue')
        ax2.set_ylabel('Sampler Meta', color='red')
        ax1.tick_params(axis='y', labelcolor='blue')
        ax2.tick_params(axis='y', labelcolor='red')

        ax1.legend([p1, p2], ['Deflection', 'Sampler Meta'], loc='best')
        fig.tight_layout()

        path = os.path.join(OUTPUT_FIGS_DIR, name)
        fig.savefig(path)
        plt.close(fig)
        assert os.path.exists(path)

        # TODO: チャンネルの最後尾にfloatの最小値が入っている。CSM-726で報告済み。
        #       現状は、各配列内でthreshold未満の値をnp.nanでマスクして対応している。
        #       matplotlibではnp.nanを無視して描画してくれる。
        # Note: XY-coordinateはmeasurementファイルのchannelに入っていない。
        #       measurementのattributesからx-offset, y-offsetとして取得。
    
    def test_coordinate_to_XY_index(self):
        """Test conversion of coordinates to XY index."""
        test_file = os.path.join(DATA_DIR, 'Forcemap-5x5.nhf')
        measurement = load_nhf_file(test_file)
        assert measurement is not None

        # Get the coordinates channel
        rect_axes = measurement.attribute['rect_axis_size']
        x_axis, y_axis = rect_axes[0], rect_axes[1]
        assert x_axis == 50
        assert y_axis == 50
        
        # Get the corner of the map as index
        left_bottom = coordinate_to_XY_index(measurement, 0, 0)
        right_bottom = coordinate_to_XY_index(measurement, 49, 0)
        right_2nd = coordinate_to_XY_index(measurement, 49, 1)
        right_top = coordinate_to_XY_index(measurement, 49, 49)
        left_top = coordinate_to_XY_index(measurement, 0, 49)
        assert left_bottom == 0
        assert right_bottom == x_axis- 1
        assert right_2nd == x_axis
        assert left_top == x_axis * y_axis - 1  # last line goes from right to left.
        assert right_top == x_axis * y_axis - x_axis


    def test_is_single_point(self):
        single_force_curve_path = os.path.join(DATA_DIR, 'ForceCurve-single.nhf')
        meas1 = load_nhf_file(single_force_curve_path)
        assert meas1 is not None
        assert is_single_point(meas1)
        forcemap_path = os.path.join(DATA_DIR, 'Forcemap-5x5.nhf')
        meas2 = load_nhf_file(forcemap_path)
        assert meas2 is not None
        assert not is_single_point(meas2)

    def test_get_first_dataset(self):
        single_force_curve_path = os.path.join(DATA_DIR, 'ForceCurve-single.nhf')
        meas1 = load_nhf_file(single_force_curve_path)
        assert meas1 is not None
        dataset1 = get_first_dataset(meas1)
        assert dataset1 is not None
        assert isinstance(dataset1, NHFDataset)
        forcemap_path = os.path.join(DATA_DIR, 'Forcemap-5x5.nhf')
        meas2 = load_nhf_file(forcemap_path)
        assert meas2 is not None
        logger.debug(f"Summary of forcemap measurement: {summary_nhf_measurement(meas2, show_channel=True, show_segment=True, show_attribute=True)}    ")
        dataset2 = get_first_dataset(meas2)
        assert dataset2 is not None
        assert isinstance(dataset2, NHFDataset)

    def test_get_offset_datapoints(self):
        """Test the calculation of offset data points."""
        forcemap_path = os.path.join(DATA_DIR, 'Forcemap-5x5.nhf')
        meas = load_nhf_file(forcemap_path)
        assert meas is not None

        deflection = meas.segment[Segment.ADVANCE].read_channel(Channel.DEFLECTION)
        z_position = meas.segment[Segment.ADVANCE].read_channel(Channel.Z_POSITION)
        logger.debug(f"deflection dataset length: {len(deflection.dataset)}, z_position dataset length: {len(z_position.dataset)}")
        logger.debug(f"count of large negative value: {np.sum(deflection.dataset < -1e+308)}, {np.sum(z_position.dataset < -1e+308)}")
        first_index_of_neg_val = np.where(deflection.dataset < -1e+308)[0].min()
        logger.debug(f"first index of large negative value in deflection: {first_index_of_neg_val}") 
        end_index_of_neg_val = np.where(deflection.dataset < -1e+308)[0].max()
        logger.debug(f"end index of large negative value in deflection: {end_index_of_neg_val}")


def test_datapoints_between_points():
    """Test the calculation of data points between two values."""
    forcemap_path = os.path.join(DATA_DIR, 'Forcemap-5x5.nhf')
    meas = load_nhf_file(forcemap_path)
    assert meas is not None

    deflection = meas.segment[Segment.ADVANCE].read_channel(Channel.DEFLECTION)
    z_position = meas.segment[Segment.ADVANCE].read_channel(Channel.Z_POSITION)
    logger.debug(f"deflection dataset length: {len(deflection.dataset)}, z_position dataset length: {len(z_position.dataset)}")
    logger.debug(f"count of large negative value: {np.sum(deflection.dataset < -1e+308)}, {np.sum(z_position.dataset < -1e+308)}")
    first_index_of_neg_val = np.where(deflection.dataset < -1e+308)[0].min()
    logger.debug(f"first index of large negative value in deflection: {first_index_of_neg_val}") 
    end_index_of_neg_val = np.where(deflection.dataset < -1e+308)[0].max()
    logger.debug(f"end index of large negative value in deflection: {end_index_of_neg_val}") 
