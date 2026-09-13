"""VEA sample point selection, independent of readers and user interfaces."""
from dataclasses import dataclass
from numbers import Integral
import re


@dataclass(frozen=True)
class PointSelection:
    width: int
    height: int
    point_indices: tuple[int, ...]

    @property
    def total_count(self):
        return self.width * self.height

    def xy(self, point_index):
        if not isinstance(point_index, Integral) or not 0 <= point_index < self.total_count:
            raise ValueError("Point index is outside the map")
        y, column = divmod(int(point_index), self.width)
        return (column if y % 2 == 0 else self.width - 1 - column), y


def select_points(width, height, *, max_count=None, crop_area=None,
                  scan_pattern="snake_bottom_left"):
    """Crop inclusive bottom-left XY bounds, then limit in acquisition order."""
    for name, value in (("width", width), ("height", height)):
        if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if max_count is not None and (isinstance(max_count, bool) or
            not isinstance(max_count, Integral) or max_count <= 0):
        raise ValueError("max_count must be a positive integer")
    width, height = int(width), int(height)
    if width * height > 1 and scan_pattern != "snake_bottom_left":
        raise ValueError(f"Unsupported scan pattern: {scan_pattern}")
    x0, y0, x1, y1 = 0, 0, width - 1, height - 1
    if crop_area is not None:
        match = re.fullmatch(r"\s*(\d+)\s*,\s*(\d+)\s*:\s*(\d+)\s*,\s*(\d+)\s*", crop_area) if isinstance(crop_area, str) else None
        if not match:
            raise ValueError('crop_area must be "x_start,y_start:x_end,y_end"')
        x0, y0, x1, y1 = map(int, match.groups())
        if not (0 <= x0 <= x1 < width and 0 <= y0 <= y1 < height):
            raise ValueError("crop_area is reversed or outside the map")
    indices = []
    for y in range(y0, y1 + 1):
        columns = range(x0, x1 + 1) if y % 2 == 0 else range(width - 1 - x1, width - x0)
        for column in columns:
            indices.append(y * width + column)
            if max_count is not None and len(indices) == max_count:
                return PointSelection(width, height, tuple(indices))
    return PointSelection(width, height, tuple(indices))


def select_sample_points(source, *, max_count=None, crop_area=None):
    """Inspect the first measurement metadata without loading waveform channels."""
    from nm_io import load_nhf_file, Segment, Channel
    measurement = load_nhf_file(source)
    size = measurement.attribute.get("rect_axis_size")
    if size is None or len(size) != 2:
        raise ValueError("Sample is missing rect_axis_size")
    channel = measurement.segment[Segment.VEA].channel[Channel.DEFLECTION]
    return select_points(*size, max_count=max_count, crop_area=crop_area,
                         scan_pattern=channel.attribute.get("signal_data_pattern"))
