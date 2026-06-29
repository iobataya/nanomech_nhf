"""NHF data container dataclasses and import functions.

This module centralizes `Measurement_Data`, `Measurement_Info` and all NHF file
loading functionality to avoid circular imports and improve modularity.
"""
from dataclasses import dataclass
import json
import numpy as np
import pathlib
from nanosurf.lib.util import nhf_reader
from typing import TypeAlias
from enum import IntEnum
import math

import logging
logger = logging.getLogger(__name__)

NHFDataset: TypeAlias = nhf_reader.NHFDataset
NHFSegment: TypeAlias = nhf_reader.NHFSegment
NHFMeasurement: TypeAlias = nhf_reader.NHFMeasurement

class Channel:
    TIME = 'Time'
    SAMPLER_META = 'Sampler Meta Channel'
    DEFLECTION = 'Deflection'
    Z_POSITION = 'Position Z'
    ANAL_2_REF = 'Analyzer 2 Reference'
    OFFSETS = 'channel_data_offsets'
    ACQ_POINTS = 'number_of_datapoints_acquired'

class Segment:
    ADVANCE = 'Advance to Setpoint 1'
    WAIT = 'Wait 1'
    VEA = 'VEA Sweep 1'
    RETRACT = 'Retract 1'

class Attribute:
    SEG_CONF = 'segment_configuration'
    BLOCK_SRC_ID = 'dataset_block_size_source'
    BLOCK_SIZE_ID = 'dataset_block_size_id'
    MAP_AXIS_SIZE_XY = 'rect_axis_size'
    PROPERTY = 'property'
    FREQ_START = 'start_frequency'
    FREQ_END = 'end_frequency'
    FREQ_DATAPTS = 'frequency_datapoints'
    SINES_PTS = 'sines_pnts'
    SINES_NUM = 'sines_number'
    SWEEP_TYPE = 'sweep_type'
    SWEEP_DIR = 'sweep_direction'
    VALUE = 'value'
    SENSITIVITY = 'spm_probe_calibration_deflection_sensitivity'
    SPRING_CONST = 'spm_probe_calibration_spring_constant'

class ContactModelName:
    Hertz = 'Hertz'
    Sneddon = 'Sneddon'
    Pyramid = 'Pyramid'
    DMT_Sphere = 'DMT_Sphere'
    DMT_Cone = 'DMT_Cone'
    DMT_Cylinder = 'DMT_Cylinder'
    DMT_Tip = 'DMT_Tip'

class SweepType(IntEnum):
    LINEAR = 0
    LOGARITHMIC = 1

class SweepDirection(IntEnum):
    ASCENDING = 0
    DESCENDING = 1


@dataclass
class Measurement_Info:
    """Summary metadata for a measurement (scan geometry and calibration).

    Commonly filled from file attributes and used for display and bookkeeping.
    """
    offset_x: float | None = None
    offset_y: float | None = None
    size_x: float | None = None
    size_y: float | None = None
    points_x: int | None = None
    points_y: int | None = None
    rotation: float | None = None

    def get_coordinates(self, point):
        """Return (X,Y) coordinates for a given point index """
        (width, height) = (self.points_x, self.points_y)
        dY = point // width
        if dY % 2 == 0:  # even row -> left to right
            X = point % width
        else:
            X = width - 1 - (point % width)
        Y = height - 1 - dY  # invert Y to start from top
        return int(X), int(Y)

class SweepConfig:
    def __init__(self, measurement:NHFMeasurement, dump:bool=False):
        if measurement is None:
            logger.warning("[SweepConfig] No measurement provided to SweepConfig constructor.")
            self.start_frequency = 0.0
            self.end_frequency = 0.0
            self.datapoints = 0
            self.sines_pnts = 0
            self.sines_number = 0
            self.sweep_type = SweepType.LINEAR
            self.sweep_direction = SweepDirection.ASCENDING
            return
    
        logger.debug(f"[SweepConfig] Attempting to load VEA configuration from measurement segments: {list(measurement.segment.keys())}")
        try:
            # perhaps the segument is named as Segment.VEA.
            if Segment.VEA in  measurement.segment.keys():
                segment_vea = measurement.segment[Segment.VEA]
            else:
                logger.debug(f"{Segment.VEA} segment not found. Attempting to use the first key in measurement.segment: {list(measurement.segment.keys())}")
                segment_vea = measurement.segment[list(measurement.segment.keys())[0]]
            segment_config = json.loads(segment_vea.attribute[Attribute.SEG_CONF])
            vea_config = segment_config[Attribute.PROPERTY]
        except:
            logger.debug(f"[SweepConfig] segment_vea:{segment_vea}")
            logger.debug(f"[SweepConfig] segment_config:{json.dumps(segment_config, indent=2, ensure_ascii=False)}")
            logger.debug(f"[SweepConfig] vea_config: {json.dumps(vea_config, indent=2, ensure_ascii=False)}")
            raise ValueError()
        if dump:
            logger.debug(f"[SweepConfig] VEA configuration loaded\n {json.dumps(vea_config, indent=2, ensure_ascii=False)}")

        try:
            v = 'value'
            self.start_frequency = float(vea_config[Attribute.FREQ_START][v])
            self.end_frequency = float(vea_config[Attribute.FREQ_END][v])
            self.datapoints = int(vea_config[Attribute.FREQ_DATAPTS][v])
            self.sines_pnts = int(vea_config[Attribute.SINES_PTS][v])
            self.sines_number = int(vea_config[Attribute.SINES_NUM][v])
            self.sweep_type: SweepType = int(vea_config[Attribute.SWEEP_TYPE][v])
            self.sweep_direction: SweepDirection = int(vea_config[Attribute.SWEEP_DIR][v])
        except KeyError:
            logger.debug(f"[SweepConfig] VEA config from file missing key(s). {vea_config}")
            raise ValueError()
        self.freq_list = self.create_frequency_list()
        if self.freq_list == None or len(self.freq_list)==0:
            logger.debug(f"[SweepConfig] Frequency list could not created. {self.config}")
            raise ValueError()


    def create_frequency_list(self) -> list:
        """Return the list of frequencies in playback order.

        For linear sweeps we interpolate linearly in frequency. For logarithmic
        sweeps we interpolate in log-space (geometric progression).
        """
        if self.datapoints <= 0:
            return None


        freq_list = []
        if self.sweep_type == SweepType.LINEAR:
            step = (self.end_frequency - self.start_frequency) / max(self.datapoints - 1, 1)
            for i in range(self.datapoints):
                f = self.start_frequency + i * step
                freq_list.append(f)
        elif self.sweep_type == SweepType.LOGARITHMIC:
            # Interpolate in log space
            log_start = math.log(self.start_frequency)
            log_end = math.log(self.end_frequency)
            step = (log_end - log_start) / max(self.datapoints - 1, 1)
            for i in range(self.datapoints):
                f = math.exp(log_start + i * step)
                freq_list.append(f)
        else:
            logger.debug(f"[SweepConfig] Unknown SweepType: {self.sweep_type}")
            raise ValueError()

        ret_freq_list: list
        if self.sweep_direction == SweepDirection.DESCENDING:
            ret_freq_list = freq_list[::-1]
        else:
            ret_freq_list = freq_list

        self.freq_list = ret_freq_list
        logger.debug(f"[SweepConfig] Frequency list created: {self.freq_list_as_integers}")
        return self.freq_list

    @property
    def freq_list_as_integers(self) -> list:
        """Return the frequency list rounded to nearest integer values."""
        if self.freq_list is None:
            return []
        return [int(round(f)) for f in self.freq_list]

    def get_common_frequencies(self, other:"SweepConfig") -> list:
        """Return a list of frequencies common to both this and another SweepConfig.

        This is useful when comparing reference and sample measurements with
        slightly different frequency lists.
        """
        if self.freq_list is None or other.freq_list is None:
            return []

        set_self = set(np.round(self.freq_list, decimals=6))
        set_other = set(np.round(other.freq_list, decimals=6))
        reverse = self.sweep_direction == SweepDirection.DESCENDING
        common = sorted(list(set_self.intersection(set_other)), reverse=reverse)
        logger.debug(f"[SC] Common frequencies between sweeps: {common}")
        return common

    def get_indices_of_frequencies(self, frequencies: list) -> list:
        """Return the indices of the given frequencies in this SweepConfig's freq_list.

        Frequencies are matched to 6 decimal places.
        """
        if self.freq_list is None:
            return []

        freq_to_index = {round(f, 6): i for i, f in enumerate(self.freq_list)}
        indices = []
        for f in frequencies:
            f_rounded = round(f, 6)
            if f_rounded in freq_to_index:
                indices.append(freq_to_index[f_rounded])
            else:
                logger.debug(f"[SweepConfig] Frequency {f} not found in freq_list.")
        logger.debug(f"[SweepConfig] Indices of given frequencies ({freq_to_index}): {indices}")
        return indices


class VeaForceMapData:
    """Holds per-point results for a force map measurement.
    Attributes:
        datasets: dictionary of NHFDataset objects accessible by [Channel][Segment]
        current_point: int - current point index being processed
    """
    def __init__(self, source_file: pathlib.Path):
        self.nhf_measurement = load_nhf_file(source_file)
        if self.nhf_measurement is None:
            raise ValueError(f"Failed to load measurement file: {source_file}")
        else:
            logger.info(f"[VFM] Measurement file loaded successfully from {source_file.name}")

        # Create SweepConfig from measurement
        self.sweep_config = SweepConfig(self.nhf_measurement)
        self.sweep_config.create_frequency_list()
        logger.info(f"[VFM] SweepConfig created: {self.sweep_config.freq_list}")

        self.datasets = {
            Channel.DEFLECTION: {
                Segment.ADVANCE: None,
                Segment.WAIT: None,
                Segment.VEA: None,
                Segment.RETRACT: None
            },
            Channel.Z_POSITION: {
                Segment.ADVANCE: None,
                Segment.WAIT: None,
                Segment.VEA: None,
                Segment.RETRACT: None
            },
            Channel.TIME: {
                Segment.ADVANCE: None,
                Segment.WAIT: None,
                Segment.VEA: None,
                Segment.RETRACT: None
            },
            Channel.SAMPLER_META: {
                Segment.ADVANCE: None,
                Segment.WAIT: None,
                Segment.VEA: None,
                Segment.RETRACT: None
            },
            Channel.ANAL_2_REF: {
                Segment.VEA: None
            }
        }
        logger.debug(f"[VFM] ForceMapData: Loading datasets from NHFMeasurement with segments: {list(self.nhf_measurement.segment.keys())}")
        for segment_name, segment in self.nhf_measurement.segment.items():
            for channel_name in self.datasets.keys():
                if channel_name in segment.channel:
                    self.datasets[channel_name][segment_name] = segment.read_channel(channel_name)
                    logger.debug(f"[VFM] Loaded dataset '{channel_name}' in datasets[{channel_name}][{segment_name}]', {len(self.datasets[channel_name][segment_name].dataset)} data points.")


        self.current_point = 0
        self.points_x = self.nhf_measurement.attribute.get('rect_axis_size', [0, 0])[0]
        self.points_y = self.nhf_measurement.attribute.get('rect_axis_size', [0, 0])[1]
        self.total_points = self.points_x * self.points_y
        self.point_indices = np.arange(self.total_points)
        self.offset_x = self.nhf_measurement.attribute.get('scanner_offset_x')
        self.offset_y = self.nhf_measurement.attribute.get('scanner_offset_y')
        self.size_x = self.nhf_measurement.attribute.get('rect_axis_range', [None, None])[0]
        self.size_y = self.nhf_measurement.attribute.get('rect_axis_range', [None, None])[1]
        self.rotation = self.nhf_measurement.attribute.get('scanner_rotation')
        logger.debug(f"[VFM] ForceMapData initialized: points_x={self.points_x}, points_y={self.points_y}, total_points={self.total_points}")
        logger.debug(f"[VFM] Offset: ({self.offset_x}, {self.offset_y}), Size: ({self.size_x}, {self.size_y}), Rotation: {self.rotation}")

    def __getitem__(self, key) -> dict[str, NHFDataset | None]:
        """Allow access to datasets via [Channel][Segment] indexing."""
        return self.datasets[key]

    def get_range_at(self, channel: str, segment: str, point: int) -> tuple:
        """Return start index and data count for the given channel, segment and spatial point index."""
        if segment not in self.datasets[channel]:
            raise ValueError(f"Segment '{segment}' not found in datasets for channel '{channel}'")
        dataset = self.datasets[channel][segment]
        if dataset is None:
            raise ValueError(f"Dataset for channel '{channel}' and segment '{segment}' is not loaded")
        # Calculate start index and data count for the given point
        offset_channel = f'channel_data_offsets'
        datapoints_channel = f'number_of_datapoints_acquired'
        try:
            offset_data = self.nhf_measurement.segment[segment].read_channel(offset_channel).dataset
            datapoints_data = self.nhf_measurement.segment[segment].read_channel(datapoints_channel).dataset
            start_index = int(offset_data[point])
            data_count = int(datapoints_data[point])
            return (start_index, data_count)
        except Exception as e:
            logger.error(f"Error retrieving data range for channel '{channel}', segment '{segment}', point {point}: {e}")
            raise

    def get_point_index(self, x: int, y: int) -> int:
        """Return point index for given (X,Y) coordinates."""
        (width, height) = (self.points_x, self.points_y)
        if x < 0 or x >= width or y < 0 or y >= height:
            raise ValueError(f"Coordinates (X={x}, Y={y}) out of bounds for map size ({width}, {height})")
        dY = height - 1 - y  # invert Y to start from top
        if dY % 2 == 0:  # even row -> left to right
            point = dY * width + x
        else:
            point = dY * width + (width - 1 - x)
        return point

    def get_coordinates(self, point):
        """Return (X,Y) coordinates for a given point index """
        (width, height) = (self.points_x, self.points_y)
        dY = point // width
        if dY % 2 == 0:  # even row -> left to right
            X = point % width
        else:
            X = width - 1 - (point % width)
        Y = height - 1 - dY  # invert Y to start from top
        return int(X), int(Y)

class ForcemapMeasurementData:
    pass


class VeaMeasurementData:
    """Holds per-measurement channels and computed arrays.

    Most attributes correspond to NHF file channels (NHFDataset instances). Computed
    arrays such as `calc_indentation_*` and `calc_force_*` are populated during import
    and analysis. Offsets/point counts are stored for segmented waveform handling.
    """
    def __init__(self):
        self.nhf_measurement:NHFMeasurement | None = None
        # Channel datasets for each segment
        self.ch_deflection_advance: NHFDataset | None = None
        self.ch_deflection_wait: NHFDataset | None = None
        self.ch_deflection_vea: NHFDataset | None = None
        self.ch_deflection_retract: NHFDataset | None = None

        self.ch_z_position_advance: NHFDataset | None = None
        self.ch_z_position_wait: NHFDataset | None = None
        self.ch_z_position_vea: NHFDataset | None = None
        self.ch_z_position_retract: NHFDataset | None = None

        self.ch_time_advance: NHFDataset | None = None
        self.ch_time_wait: NHFDataset | None = None
        self.ch_time_vea: NHFDataset | None = None
        self.ch_time_retract: NHFDataset | None = None

        self.ch_meta_advance: NHFDataset | None = None
        self.ch_meta_wait: NHFDataset | None = None
        self.ch_meta_vea: NHFDataset | None = None
        self.ch_meta_retract: NHFDataset | None = None

        self.ch_reference_vea: NHFDataset | None = None

        # Calculated arrays
        self.calc_indentation_advance: np.ndarray | None = None
        self.calc_indentation_wait: np.ndarray | None = None
        self.calc_indentation_vea: np.ndarray | None = None
        self.calc_indentation_retract: np.ndarray | None = None

        self.calc_force_advance: np.ndarray | None = None
        self.calc_force_wait: np.ndarray | None = None
        self.calc_force_vea: np.ndarray | None = None
        self.calc_force_retract: np.ndarray | None = None

        # Data segmentation arrays
        self.data_offsets_advance: np.ndarray | None = None
        self.data_offsets_wait: np.ndarray | None = None
        self.data_offsets_vea: np.ndarray | None = None
        self.data_offsets_retract: np.ndarray | None = None

        self.datapoints_acquired_advance: np.ndarray | None = None
        self.datapoints_acquired_wait: np.ndarray | None = None
        self.datapoints_acquired_vea: np.ndarray | None = None
        self.datapoints_acquired_retract: np.ndarray | None = None

        self.force_map: VeaForceMapData | None = None

        # Configuration and metadata
        self.vea_configuration: dict | None = None
        self.sweep_config: "SweepConfig" | None = None
        #self.sweep_config: "SweepConfig" | None = None
        self.wait_exists: bool = False

    def subtract_indentation(self, z_offset: float):
        """Subtract a constant offset from all indentation channels."""
        if self.calc_indentation_advance is not None:
            self.calc_indentation_advance -= z_offset
        if self.calc_indentation_wait is not None:
            self.calc_indentation_wait -= z_offset
        if self.calc_indentation_vea is not None:
            self.calc_indentation_vea -= z_offset
        if self.calc_indentation_retract is not None:
            self.calc_indentation_retract -= z_offset

    @staticmethod
    # Compares the VEA settings (Reference Data vs. Measurement Data)
    def compare_vea_properties(vea_data_1:"VeaMeasurementData", vea_data_2:"VeaMeasurementData") -> bool:
        properties = ["start_frequency","end_frequency","sweep_type","sweep_direction","sines_number","sines_pnts"]
        for prop in properties:  # check except for datapoints
            if vea_data_1.vea_configuration["property"][prop] != vea_data_2.vea_configuration["property"][prop]:
                logger.error(f"VEA property '{prop}' mismatch: {vea_data_1.vea_configuration['property'][prop]['value']} != {vea_data_2.vea_configuration['property'][prop]['value']}")
                return False
        # check frequency datapoints
        if int(vea_data_1.vea_configuration["property"]["frequency_datapoints"]['value']) == int(vea_data_2.vea_configuration["property"]["frequency_datapoints"]['value']):
            logger.info("VEA properties match between reference and sample measurement.")
            return True
        else:
            logger.warning(f"VEA property 'frequency_datapoints' mismatch: {vea_data_1.vea_configuration['property']['frequency_datapoints']['value']} != {vea_data_2.vea_configuration['property']['frequency_datapoints']['value']}")
            logger.info("Trying to find matched frequencies between reference and sample measurement...")

            return False


    @staticmethod
    def get_measurement_info(measurement:NHFMeasurement) -> Measurement_Info:
        info = Measurement_Info(
            offset_x=measurement.attribute.get('scanner_offset_x'),
            offset_y=measurement.attribute.get('scanner_offset_y'),
            size_x=measurement.attribute.get('rect_axis_range', [None, None])[0],
            size_y=measurement.attribute.get('rect_axis_range', [None, None])[1],
            points_x=measurement.attribute.get('rect_axis_size', [None, None])[0],
            points_y=measurement.attribute.get('rect_axis_size', [None, None])[1],
            rotation=measurement.attribute.get('rect_rotation'),
        )
        return info

# Reads offsets and number of datapoints for File-Loading
def get_offset_datapoints(segment: NHFSegment, channel: NHFDataset):
    offset = None
    datapoints = None

    try:
        ch_offset = segment.read_channel('channel_data_offsets')
        ch_datapoints = segment.read_channel('number_of_datapoints_acquired')
        offset = ch_offset.dataset
        datapoints = ch_datapoints.dataset
    except Exception as e:
        logger.debug(f"No offset and datapoint channel found in the segment {segment.name}. Falling back to block-size method...")
        try:
            block_size_id = channel.attribute["dataset_block_size_source"]
            datap = segment.find_dataset_by_attribute_value("dataset_block_size_id", block_size_id)
            logger.debug(f"Found block_size_id `{block_size_id}` in segment `{segment.name}`,  {len(datap)} point(s).")
            offset = np.cumsum(datap)
            offset = np.insert(offset, 0, 0)
            datapoints = np.diff(offset)
            logger.debug(f"Offset indices for XY points: {repr(offset)}")
        except Exception as e:
            logger.error(f"Warning: No data with number of acquired datapoints found: {e}")
            raise

    if offset is None or datapoints is None:
        logger.error(f"Unable to determine offsets/datapoints for segment {segment.name}")
        raise ValueError(f"Unable to determine offsets/datapoints for segment {segment.name}")

    return offset, datapoints



def convert_deflection_to_meters(ch_defl: NHFDataset, measurement: NHFMeasurement, deflection_sensitivity: float | None = None, spring_constant: float | None = None):
    """ Convert deflection channel to meters using sensitivity and spring constant."""
    ds = deflection_sensitivity
    sc = spring_constant

    if ds is None or sc is None:
        # fall back to measurement attributes if context not set
        ds = measurement.attribute.get(Attribute.SENSITIVITY, ds)
        sc = measurement.attribute.get(Attribute.SPRING_CONST, sc)

    if (ch_defl.unit == 'V'):
        ch_defl.dataset *= ds
        logger.debug(f"Deflection channel '{ch_defl.name}' converted from V to m using sensitivity {ds} m/V")
    elif (ch_defl.unit == 'm'):
        logger.debug(f"Deflection channel '{ch_defl.name}' already in m, no conversion applied")
    elif (ch_defl.unit == 'N'):
        ch_defl.dataset /= sc
        logger.debug(f"Deflection channel '{ch_defl.name}' converted from N to m using spring constant {sc} N/m")
    else:
        logger.warning(f"Deflection channel '{ch_defl.name}' has unknown unit '{ch_defl.unit}', no conversion applied")


def find_frequency_changes(data: VeaMeasurementData, point:int):
    """ Find indices where the excitation frequency changes within a measurement point of force-map."""
    start_index = int(data.data_offsets_vea[point])
    end_index = int(start_index + data.datapoints_acquired_vea[point]-2)
    # diff makes non-zero value when frequency changes.
    # [10, 10, 10, 20, 20, 30, 30, 30] → [0, 0, 10, 0, 10, 0, 0]
    diff = np.diff(data.ch_meta_vea.dataset[start_index:end_index])
    change_indices = np.where(diff != 0)[0]  # indecies of boundaries.
    change_indices = np.append(change_indices, end_index)  # add the last index.
    corr_change_indices = change_indices + 1 # +1 to correct for diff offset

    #logger.debug(f"find_frequency_changes found at xy-point({point}) from {start_index} to {end_index}")
    #logger.debug(f"change_indices: {corr_change_indices}, val: {data.ch_meta_vea.dataset[corr_change_indices + start_index]}")
    return corr_change_indices

def load_nhf_file(source_file: pathlib.Path) -> NHFMeasurement:
    """Load an NHF file and return the first measurement instance.

    This function is defensive: it validates the input path, converts to a
    pathlib.Path if needed, checks file existence and uses a non-verbose
    NHFFileReader to avoid environment-dependent side-effects.
    """
    if not source_file:
        raise ValueError("No source_file provided to load_nhf_file")

    source = pathlib.Path(source_file)
    try:
        source_resolved = source.resolve()
    except Exception:
        source_resolved = source

    if not source.exists():
        raise FileNotFoundError(f"NHF file not found: {source_resolved}")

    try:
        nhf_file = nhf_reader.NHFFileReader(source_resolved, verbose=False)
    except Exception as e:
        raise ValueError(f"Failed to open NHF file '{source_resolved}': {e}") from e

    if not nhf_file.measurement:
        raise ValueError(f"No measurement found in NHF file: {source_resolved}")

    # Best-effort version check (non-fatal if unavailable)
    try:
        ver = nhf_file.version()
        if ver < (2, 1):
            raise ValueError(f"Unsupported NHF version {ver} in file: {source_resolved}")
    except Exception:
        logger.warning(f"Could not determine NHF file version for: {source_resolved}")

    measurement_name = nhf_file.measurement_name(0)
    measurement = nhf_file.measurement[measurement_name]

    # Log available segments for debugging when files differ between systems
    try:
        seg_names = list(measurement.segment.keys())
        logger.debug(f"Segments available: {seg_names}")
    except Exception:
        logger.debug(f"Could not enumerate measurement.segment keys; segment object repr: {measurement!r}")
        raise ValueError(f"Failed to enumerate measurement.segment keys for: {source_resolved}")

    return measurement
