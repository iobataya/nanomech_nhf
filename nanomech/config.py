"""Validated VEA file settings; explicit CLI arguments always take precedence."""
import argparse
import json
from pathlib import Path
import tomllib


SECTIONS = {
    "cli": {"sample", "calibration", "output", "max_count", "max_points", "crop_area",
            "log_level", "dry_run", "plot_sample", "plot_calibration", "max_plot_sample",
            "excitation", "correct_drag"},
    "probe": {"tip_radius", "cone_half_angle", "poisson_ratio", "sensitivity", "spring_constant"},
    "static": {"model", "fit_direction", "baseline_start", "baseline_end"},
}


def read_config(path):
    with path.open("rb") as stream:
        return tomllib.load(stream) if path.suffix.lower() == ".toml" else json.loads(stream.read().decode("utf-8"))


def apply_vea_config(args, parser, command="vea"):
    if not args.config:
        args.file_config = {}
        return
    path = args.config
    is_toml = path.suffix.lower() == ".toml"
    data = read_config(path)
    if not isinstance(data, dict) or data.get("schema_version") != 1 or data.get("command") != command:
        raise ValueError(f"Config requires schema_version=1 and command={command}")
    sections = SECTIONS if command == "vea" else {"cli": {"input", "output", "log_level"}}
    settings = {}
    allowed = set().union(*sections.values())
    def add(key, value):
        if key not in allowed:
            raise ValueError(f"Unknown {command} config key: {key}")
        key = "max_count" if key == "max_points" else key
        if key in settings:
            raise ValueError(f"Duplicate {command} config key: {key}")
        settings[key] = value
    for key, value in data.items():
        if key in ("schema_version", "command"):
            continue
        if key in sections:
            if not isinstance(value, dict):
                raise ValueError(f"{key} must be a table")
            for option, setting in value.items():
                if option not in sections[key]:
                    raise ValueError(f"Unknown {key} config key: {option}")
                add(option, setting)
        else:
            add(key, value)
    actions = {action.dest: action for action in parser._actions}
    for key, value in settings.items():
        action = actions[key]
        if isinstance(action, argparse.BooleanOptionalAction):
            valid = type(value) is bool
        elif action.type is int:
            valid = type(value) is int
        elif action.type is float:
            valid = type(value) in (int, float)
        else:
            valid = isinstance(value, str)
        if not valid:
            raise ValueError(f"Invalid config value type for {key}: {value!r}")
        value = action.type(value) if action.type else value
        if action.choices and value not in action.choices:
            raise ValueError(f"Invalid config value for {key}: {value!r}")
        if is_toml and isinstance(value, Path) and not value.is_absolute():
            value = (path.resolve().parent / value).resolve()
        settings[key] = value
    args.file_config = settings
    for key, value in settings.items():
        # Preserve probe provenance for the existing resolution pipeline.
        if key not in ("sensitivity", "spring_constant") and getattr(args, key) is None:
            setattr(args, key, value)
