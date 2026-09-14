"""VEA CLI arguments and conversion to the shared request API."""
from pathlib import Path
import argparse
from dataclasses import asdict

from .requests import VeaRequest, ProbeOverrides
from .static import StaticConfig
from . import workflows


def configure_parser(parser):
    parser.add_argument("--sample", type=Path)
    parser.add_argument("--calibration", type=Path,
                        help="Calibration NHF; omitted uses .last_calibration.nhf beside main.py")
    parser.add_argument("--config", type=Path)
    from nanomech.nm_models import canonical_contact_model, CONTACT_MODELS
    parser.add_argument("--model",type=canonical_contact_model,choices=CONTACT_MODELS)
    parser.add_argument("--cone-half-angle", "--cone_half_angle",type=float,help="Cone/pyramid half angle in degrees")
    parser.add_argument("--excitation", choices=("auto","Piezo","CleanDrive"))
    parser.add_argument("--correct-drag", action=argparse.BooleanOptionalAction, default=None,
                        help="Piezo hydrodynamic drag correction (default enabled)")
    parser.add_argument("--fit-direction", "--fit_direction", type=str.capitalize, choices=("Advance", "Retract"))
    parser.add_argument("--tip-radius", "--tip_radius", type=float, help="Hertz sphere radius in metres")
    parser.add_argument("--poisson-ratio", "--poisson_ratio", type=float)
    parser.add_argument("--baseline-start", "--baseline_start", type=float)
    parser.add_argument("--baseline-end", "--baseline_end", type=float)
    parser.add_argument("--plot-calibration", action=argparse.BooleanOptionalAction, default=None,
                        help="Save all calibration frequencies vertically in one deflection/fit PNG")
    parser.add_argument("--plot-sample", action=argparse.BooleanOptionalAction, default=None,
                        help="Save sample force/indentation PNGs with fitted curves")
    parser.add_argument("--max-plot-sample", type=int,
                        help="Maximum sample PNGs; omitted means all successful selected points (0 disables plots)")
    parser.add_argument("--output", type=Path, help="Output root for results and plots (default: results)")
    parser.add_argument("--sensitivity", type=float, help="Deflection sensitivity in m/V")
    parser.add_argument("--spring_constant", "--spring-constant", type=float, help="Spring constant in N/m")
    parser.add_argument("--max_count", "--max-count", "--max_points", "--max-points",
                        dest="max_count", type=int, help="Maximum attempted sample points, after crop")
    parser.add_argument("--crop_area", "--crop-area", dest="crop_area",
                        help='Inclusive bottom-left XY bounds: "x_start,y_start:x_end,y_end"')
    parser.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=None,
                        help="Select sample points and fit calibration; skip sample analysis")


def request_from_args(args):
    """Convert already merged CLI/file settings, preserving probe provenance."""
    config = getattr(args, "file_config", {})
    source = args.sample if args.sample is not None else config.get("sample")
    if not source:
        raise ValueError("--sample or config sample is required")
    static = StaticConfig(**{
        key: getattr(args, key) if getattr(args, key) is not None else config.get(key, value)
        for key, value in asdict(StaticConfig()).items()
    })
    return VeaRequest(
        sample=Path(source), calibration=args.calibration,
        output=Path(args.output or config.get("output", "results")),
        static=static, max_count=args.max_count, crop_area=args.crop_area,
        dry_run=bool(args.dry_run), plot_calibration=bool(args.plot_calibration),
        plot_sample=bool(args.plot_sample), max_plot_sample=args.max_plot_sample,
        excitation=args.excitation or "auto",
        correct_drag=args.correct_drag if args.correct_drag is not None else True,
        probe=ProbeOverrides(args.sensitivity, args.spring_constant),
        probe_config=ProbeOverrides(config.get("sensitivity"), config.get("spring_constant")),
        probe_source="CLI", config_path=args.config,
    )


def execute(args):
    result = workflows.run_vea(request_from_args(args))
    return 1 if result.status == "failed" else 0
