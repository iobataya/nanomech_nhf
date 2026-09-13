"""Command registration and noninteractive file output."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from uuid import uuid4


def excitation_parser(parser):
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--config", type=Path)


def excitation_execute(args):
    from .workflows import excitation_fit

    config = {}
    if args.config:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        if not isinstance(config, dict) or config.get("schema_version") != 1 or config.get("command") != "excitation-fit":
            raise ValueError("Config requires schema_version=1 and command=excitation-fit")
        if set(config) - {"schema_version", "command", "input", "output"}:
            raise ValueError("Unknown config keys")
    source = args.input or config.get("input")
    if not source:
        raise ValueError("--input or config input is required")
    source = Path(source)
    output = Path(args.output or config.get("output", "results"))
    result, provenance = excitation_fit(source)
    run = output / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex)
    run.mkdir(parents=True, exist_ok=False)
    metadata = {"schema_version": 1, "command": "excitation-fit", "input": str(source.resolve()),
                "measurement_index": 0, "point_index": 0, "amplitude_unit": "m",
                **provenance,
                "frequency_unit": "Hz", "log_base": 10, "status": "success", **asdict(result)}
    (run / "run.json").write_text(json.dumps(metadata, indent=2, allow_nan=False), encoding="utf-8")
    (run / "excitation_coefficients.json").write_text(
        json.dumps(dict(zip((f"c{i}" for i in range(6)), result.coefficients)), indent=2, allow_nan=False), encoding="utf-8")
    print(run)
    return 0


COMMANDS = (("excitation-fit", "Fit excitation coefficients from NHF point zero", excitation_parser, excitation_execute),)


def main(argv=None):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=True)
    names = set()
    for name, summary, configure, execute in COMMANDS:
        if name in names:
            raise ValueError(f"Duplicate command: {name}")
        names.add(name)
        child = subparsers.add_parser(name, help=summary)
        configure(child)
        child.set_defaults(handler=execute)
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
