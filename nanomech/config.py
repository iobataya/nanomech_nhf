"""Validated VEA file settings; explicit CLI arguments always take precedence."""
import json
from pathlib import Path
import tomllib
import shutil
import logging


def copy_run_config(source, run):
    """Archive the original settings without colliding with result filenames."""
    if source is None:
        return
    source = Path(source)
    destination = Path(run) / ("input_config" + source.suffix)
    shutil.copy2(source, destination)
    logging.getLogger(__name__).info("Config copied: %s -> %s", source, destination)


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


def load_settings(path, command=None):
    """Read validated settings shared by CLI and GUI, without starting analysis.

    TOML paths are relative to the settings file; JSON preserves legacy paths.
    Missing options are omitted so each interface can apply its defaults.
    """
    path = Path(path)
    is_toml = path.suffix.lower() == ".toml"
    data = read_config(path)
    selected = data.get("command") if isinstance(data, dict) else None
    if not isinstance(selected, str) or selected not in ("vea", "excitation-fit"):
        raise ValueError("Config command must be excitation-fit or vea")
    command = selected if command is None else command
    if data.get("schema_version") != 1 or selected != command:
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
    paths = {"sample", "calibration", "output", "input"}
    booleans = {"dry_run", "plot_sample", "plot_calibration", "correct_drag"}
    integers = {"max_count", "max_plot_sample"}
    floats = {"tip_radius", "cone_half_angle", "poisson_ratio", "sensitivity", "spring_constant",
              "baseline_start", "baseline_end"}
    choices = {
        "excitation": ("auto", "Piezo", "CleanDrive"),
        "fit_direction": ("Advance", "Retract"),
        "log_level": ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
    }
    for key, value in settings.items():
        if key in booleans:
            valid = type(value) is bool
        elif key in integers:
            valid = type(value) is int
        elif key in floats:
            valid = type(value) in (int, float)
        else:
            valid = isinstance(value, str)
        if not valid:
            raise ValueError(f"Invalid config value type for {key}: {value!r}")
        if key in paths:
            value = Path(value)
        elif key in floats:
            value = float(value)
        elif key == "model":
            from .nm_models import canonical_contact_model
            value = canonical_contact_model(value)
        elif key == "fit_direction":
            value = value.capitalize()
        elif key == "log_level":
            value = value.upper()
        if key in choices and value not in choices[key]:
            raise ValueError(f"Invalid config value for {key}: {value!r}")
        if is_toml and isinstance(value, Path) and not value.is_absolute():
            value = (path.resolve().parent / value).resolve()
        settings[key] = value
    return command, settings


def apply_vea_config(args, parser, command="vea"):
    """Apply shared file settings while preserving explicit CLI overrides."""
    if not args.config:
        args.file_config = {}
        return
    _, settings = load_settings(args.config, command)
    args.file_config = settings
    for key, value in settings.items():
        # Preserve probe provenance for the existing resolution pipeline.
        if key not in ("sensitivity", "spring_constant") and getattr(args, key) is None:
            setattr(args, key, value)
