"""VEA selection preview; numerical VEA service will use the same selection."""
import json
import logging
from pathlib import Path

from .selection import select_sample_points

logger = logging.getLogger(__name__)


def configure_parser(parser):
    parser.add_argument("--sample", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--max_count", "--max-count", "--max_points", "--max-points",
                        dest="max_count", type=int, help="Maximum attempted sample points, after crop")
    parser.add_argument("--crop_area", "--crop-area", dest="crop_area",
                        help='Inclusive bottom-left XY bounds: "x_start,y_start:x_end,y_end"')
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview selection without loading waveforms or running analysis")


def execute(args):
    config = {}
    if args.config:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        if not isinstance(config, dict) or config.get("schema_version") != 1 or config.get("command") != "vea":
            raise ValueError("Config requires schema_version=1 and command=vea")
        if set(config) - {"schema_version", "command", "sample", "max_count", "max_points", "crop_area"}:
            raise ValueError("Unknown VEA config keys")
        if "max_count" in config and "max_points" in config:
            raise ValueError("Specify only one of max_count and max_points in config")
    source = args.sample if args.sample is not None else config.get("sample")
    if not source:
        raise ValueError("--sample or config sample is required")
    if not args.dry_run:
        raise ValueError("VEA analysis is not implemented yet; use --dry-run to verify point selection")
    limit = args.max_count if args.max_count is not None else config.get("max_count", config.get("max_points"))
    crop = args.crop_area if args.crop_area is not None else config.get("crop_area")
    limit_label = "ALL" if limit is None else limit
    crop_label = "ALL" if crop is None else crop
    logger.debug("VEA selection options: crop_area=%s, max_count=%s", crop_label, limit_label)
    selection = select_sample_points(Path(source), max_count=limit, crop_area=crop)
    logger.info("VEA selection preview: %d / %d points, map=%dx%d, max_count=%s, crop_area=%s",
                len(selection.point_indices), selection.total_count, selection.width, selection.height, limit_label, crop_label)
    preview = selection.point_indices[:20]
    logger.info("Selected acquisition indices (first 20): %s", list(preview))
    logger.info("Selected XY (first 20): %s", [selection.xy(i) for i in preview])
    return 0
