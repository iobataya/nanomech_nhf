"""Helpers for Gwyddion/GWY export and storage.

"""
from __future__ import annotations
import numpy as np
from typing import List
import pathlib
from nanomech.gwy_export import GwySizeInfo, savedata_gwy

class NmGwyContainer:
    """Two-dimensional container of result values (np.float64).

    The container stores an object per (channel, y, x) coordinate in an internal
    numpy array with dtype=np.float64. It provides convenience accessors for
    setting a value and retrieving all results (optionally flipping y).
    """
    def __init__(self, channel_size: int, y_size: int, x_size: int, physSizeInfo: GwySizeInfo) -> None:
        # Initialize a 3D array of result objects
        self.map = np.empty((channel_size, y_size, x_size), dtype=np.float64)
        # Fill with np.nan values to avoid uninitialized values
        self.map.fill(np.nan)
        self.physicalSize = physSizeInfo

    def set_result(self, channel: int, y: int, x: int, result:np.float64) -> None:
        """Set the value stored at coordinate (channel, y, x)."""
        self.map[channel, y, x] = np.float64(result)

    def to_list(self) -> List[np.ndarray]:
        """Return a list of 2D slices (one per channel) representing the map.
        """
        return [self.map[ch, :, :] for ch in range(self.map.shape[0])]
        
    def save_as_gwy(self, measurement_file: str | pathlib.Path, data_labels: list[str], data_units: list[str], path_prefix: str="", meta_data=None) -> str:
        """Save the container as a GWY file next to the measurement file.

        Parameters
        - measurement_file: path to the original measurement file (Path or string)
        - result_maps: NmGwyContainer instance
        - data_labels: list of strings
        - data_units: list of strings
        - path_prefix: optional prefix for the output filename
        - meta_data: optional dictionary of metadata

        Returns
        - path (str) of the saved GWY file
        """
        # Accept either a Path or string and compute output path next to measurement
        measurement_path = pathlib.Path(measurement_file)
        parent = measurement_path.parent if measurement_path.parent != pathlib.Path('') else pathlib.Path.cwd()
        out_name = f"{path_prefix}{measurement_path.stem}.gwy"
        out_path = parent / out_name

        data_sets = self.to_list()

        if meta_data is None:
            meta_data = {
            'path': str(measurement_path),
            }

        savedata_gwy(str(out_path), 
                                size_info=self.physicalSize,
                                data_sets=data_sets,
                                data_labels=data_labels,
                                data_units=data_units,
                                meta_data=meta_data,
                                )
        return str(out_path)