"""Export the same static/dynamic tables as CSV to spatial Gwyddion maps."""
import json
import logging
from pathlib import Path
import numpy as np
from nanomech.nm_io import load_nhf_file
from nanomech.nm_gwy import NmGwyContainer
from nanomech.gwy_export import GwySizeInfo, savedata_gwy

STATIC = (
    ("contact_point_m", "Contact Point", "m"),
    ("young_modulus_pa", "Young Modulus", "Pa"),
    ("adhesion_parameter_n_per_m", "DMT Gamma", "N/m"),
    ("snap_in_force_n", "Force of Snap-In", "N"),
    ("adhesion_force_n", "Force of Adhesion", "N"),
)
DYNAMIC = (("storage_modulus_pa", "E Store", "Pa"),
           ("loss_modulus_pa", "E Loss", "Pa"),
           ("loss_tangent", "Loss Tangent", ""))


def export_gwyddion(path, sample, selection, static, dynamic, frequencies, metadata):
    attributes = load_nhf_file(Path(sample)).attribute
    ranges = np.asarray(attributes.get("rect_axis_range"), dtype=float)
    offsets = np.array([attributes.get("scanner_offset_x", 0.), attributes.get("scanner_offset_y", 0.)],dtype=float)
    if ranges.shape != (2,) or not np.all(np.isfinite(ranges)) or np.any(ranges <= 0) or not np.all(np.isfinite(offsets)):
        raise ValueError("Invalid NHF map ranges/offsets for Gwyddion export")
    size = GwySizeInfo(float(ranges[0]), float(ranges[1]), float(offsets[0]), float(offsets[1]))
    container = NmGwyContainer(5+3*len(frequencies),selection.height,selection.width,size)
    labels, units = [], []
    def coordinates(rows):
        indices = rows.point_index.to_numpy(dtype=np.intp)
        if np.any(indices < 0) or np.any(indices >= selection.total_count):
            raise ValueError("Point index is outside the map")
        y, column = np.divmod(indices, selection.width)
        x = np.where(y % 2 == 0, column, selection.width - 1 - column)
        # CSV uses bottom-left coordinates; GWY raster starts at the top row.
        return selection.height - 1 - y, x

    # Explicitly retain the old loop's last-row-wins behavior for duplicates.
    static = static.drop_duplicates("point_index", keep="last")
    static_y, static_x = coordinates(static)
    for channel,(column,label,unit) in enumerate(STATIC):
        container.map[channel, static_y, static_x] = static[column].to_numpy(dtype=float)
        labels.append(label)
        units.append(unit)

    dynamic = dynamic.loc[dynamic.frequency_index.isin(range(len(frequencies)))]
    dynamic = dynamic.drop_duplicates(["point_index", "frequency_index"], keep="last")
    dynamic_y, dynamic_x = coordinates(dynamic)
    frequency_indices = dynamic.frequency_index.to_numpy()
    values = dynamic[[column for column, _, _ in DYNAMIC]].to_numpy(dtype=float)
    for j in range(len(frequencies)):
        selected = frequency_indices == j
        channels = 5 + np.arange(len(DYNAMIC)) * len(frequencies) + j
        container.map[channels[:, None], dynamic_y[selected], dynamic_x[selected]] = values[selected].T
    for kind,(column,label,unit) in enumerate(DYNAMIC):
        for j,frequency in enumerate(frequencies):
            labels.append(f"{label} {frequency:.12g} Hz")
            units.append(unit)
    meta = {"analysis":json.dumps(metadata,ensure_ascii=False,allow_nan=False),
            "source":str(Path(sample).resolve()),
            "scanner_rotation":str(attributes.get("scanner_rotation",0)),
            "coordinates":"NHF X/Y axes; bottom-left snake scan; raster Y flipped; rotation stored without resampling",
            "status":"Unprocessed=0, failed=NaN (masked); detailed status/reasons in CSV"}
    if not savedata_gwy(Path(path),size,container.to_list(),labels,units,meta_data=meta):
        raise OSError(f"Failed to save Gwyddion results: {path}")
    logging.getLogger(__name__).info("Gwyddion results saved: %s (%d channels)",path,len(labels))
    return Path(path)
