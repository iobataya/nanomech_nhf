import os
import sys
import numpy as np
import matplotlib.pyplot as plt

# Ensure repository root is on sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nanomech.nm_gwy import NmGwyContainer, GwySizeInfo

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'results')
OUTPUT_FIGS_DIR = os.path.join(os.path.dirname(__file__), 'figs')
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
FORCEMAP_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test-data-large', 'Forcemap-50x50.nhf'))
def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

from nanomech.nm_io import *

NHFDataset: TypeAlias = nhf_reader.NHFDataset
NHFSegment: TypeAlias = nhf_reader.NHFSegment
NHFMeasurement: TypeAlias = nhf_reader.NHFMeasurement

def test_load_nsf_measurement():
    """Test loading of a .nsf file."""
    test_file = Path(FORCEMAP_FILE)

    nsf_measurement = NSF_Measurement(test_file)
    assert nsf_measurement is not None
    assert nsf_measurement.is_nhf
    logger.info(f"NSF_Measurement loaded from {test_file} (reader type: {type(nsf_measurement.reader)}) with {nsf_measurement.reader.measurement_count()} measurement(s).")

def test_load_nhf_file():
    """Test loading of a .nhf file."""
    test_file = FORCEMAP_FILE

    nhf_file = nhf_reader.NHFFileReader(verbose=True)
    assert nhf_file.read(test_file)

    logger.info(f"NHF file loaded from {test_file}")
    logger.info(f"Reader object type:  {type(nhf_file)}")

def test_load_nhf_forcemapping():
    """Test loading of a .nhf file."""
    test_file = FORCEMAP_FILE

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
    

def test_load_nhf_single_forcecurve_file():
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
    #logger.info(nhf_summary)

    # measurement.segment is a dictionary with keys 'advance' and 'retract'
    assert measurement.segment is not None
    assert Segment.ADVANCE in measurement.segment
    assert Segment.RETRACT in measurement.segment

    # segment[Segment.ADVANCE] is a dictionary with keys of channels.
    advance_segment = measurement.segment[Segment.ADVANCE]
    x = advance_segment.read_channel(Channel.Z_POSITION)
    y = advance_segment.read_channel(Channel.DEFLECTION)
    meta = advance_segment.read_channel(Channel.SAMPLER_META)
    time_ch = advance_segment.read_channel(Channel.TIME)

    name = "test_nhf_forcespec.png"
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()

    # Plot two parameters against the same x-axis with separate y-axes.
    p1 = ax1.scatter(x.get_masked_dataset(), y.get_masked_dataset(), s=8, color='blue', label='Deflection')
    p2 = ax2.scatter(x.get_masked_dataset(), meta.get_masked_dataset(), s=8, color='red', label='Sampler Meta')

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

    name = "test_nhf_forcespec_by_time.png"
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()

    # Plot two parameters against the same x-axis with separate y-axes.
    p1 = ax1.scatter(time_ch.get_masked_dataset(), y.get_masked_dataset(), s=8, color='blue', label='Deflection')
    p2 = ax2.scatter(time_ch.get_masked_dataset(), meta.get_masked_dataset(), s=8, color='red', label='Position Z')

    ax1.set_xlabel('Time')
    ax1.set_ylabel('Deflection', color='blue')
    ax2.set_ylabel('Position Z', color='red')
    ax1.tick_params(axis='y', labelcolor='blue')
    ax2.tick_params(axis='y', labelcolor='red')

    ax1.legend([p1, p2], ['Deflection', 'Position Z'], loc='best')
    fig.tight_layout()

    path = os.path.join(OUTPUT_FIGS_DIR, name)
    fig.savefig(path)
    plt.close(fig)

    assert os.path.exists(path)

    # Note: datasetの末尾にはfloatの最小値が入っている。read_channelで読み込む。
    # Note: XY-coordinateはmeasurementファイルのchannelに入っていない。
    #       measurementのattributesからx-offset, y-offsetとして取得。

def test_coordinate_to_XY_index():
    """Test conversion of coordinates to XY index."""
    test_file = FORCEMAP_FILE
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


def test_is_single_point():
    single_force_curve_path = os.path.join(DATA_DIR, 'ForceCurve-single.nhf')
    meas1 = load_nhf_file(single_force_curve_path)
    assert meas1 is not None
    assert is_single_point(meas1)
    forcemap_path = FORCEMAP_FILE
    meas2 = load_nhf_file(forcemap_path)
    assert meas2 is not None
    assert not is_single_point(meas2)

def test_get_first_dataset():
    single_force_curve_path = os.path.join(DATA_DIR, 'ForceCurve-single.nhf')
    meas1 = load_nhf_file(single_force_curve_path)
    assert meas1 is not None
    dataset1 = get_first_dataset(meas1)
    assert dataset1 is not None
    assert isinstance(dataset1, NHFDataset)
    forcemap_path = FORCEMAP_FILE
    meas2 = load_nhf_file(forcemap_path)
    assert meas2 is not None
    logger.debug(f"Summary of forcemap measurement: {summary_nhf_measurement(meas2, show_channel=True, show_segment=True, show_attribute=True)}    ")
    dataset2 = get_first_dataset(meas2)
    assert dataset2 is not None
    assert isinstance(dataset2, NHFDataset)

def test_get_offset_datapoints():
    """Test the calculation of offset data points."""
    forcemap_path = FORCEMAP_FILE
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
    forcemap_path = FORCEMAP_FILE
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
