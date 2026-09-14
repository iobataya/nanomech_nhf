"""Command registration and noninteractive file output."""
import argparse
from pathlib import Path
import logging
import sys
from .logging_config import configure_logging
from . import vea_command

logger = logging.getLogger(__name__)


def excitation_parser(parser):
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--config", type=Path)


def excitation_execute(args):
    config = getattr(args, "file_config", {})
    source = args.input or config.get("input")
    if not source:
        raise ValueError("--input or config input is required")
    from .requests import ExcitationFitRequest
    from .workflows import run_excitation_fit
    result = run_excitation_fit(ExcitationFitRequest(
        source=Path(source), output=Path(args.output or config.get("output", "results")),
        config_path=args.config,
    ))
    return 1 if result.status == "failed" else 0


COMMANDS = (
    ("excitation-fit", "Fit excitation coefficients from NHF point zero", excitation_parser, excitation_execute),
    ("vea", "Prepare calibration and fit static sample response", vea_command.configure_parser, vea_command.execute),
)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        epilog="Use --config FILE.toml without a subcommand to run the file's command.")
    log_options = dict(type=str.upper, choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
                       help="Console log level (default: INFO)")
    parser.add_argument("--log-level", "--log_level", default=None, **log_options)
    subparsers = parser.add_subparsers(required=True)
    names = set()
    for name, summary, configure, execute in COMMANDS:
        if name in names:
            raise ValueError(f"Duplicate command: {name}")
        names.add(name)
        child = subparsers.add_parser(name, help=summary)
        child.add_argument("--log-level", "--log_level", default=argparse.SUPPRESS, **log_options)
        configure(child)
        child.set_defaults(handler=execute, command_parser=child, command_name=name)
    # Read only shared options before selecting the full command parser.
    bootstrap = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    bootstrap.add_argument("--config", type=Path)
    bootstrap.add_argument("--log-level", "--log_level")
    preliminary, remaining = bootstrap.parse_known_args(argv)
    if preliminary.config and not (remaining and remaining[0] in names):
        from .config import read_config
        try:
            config = read_config(preliminary.config)
            command = config.get("command") if isinstance(config, dict) else None
            if not isinstance(command, str) or command not in names:
                raise ValueError("Config command must be excitation-fit or vea")
        except (ValueError, OSError) as error:
            configure_logging("INFO")
            logger.info("error: %s", error)
            return 1
        argv.insert(0, command)
    args = parser.parse_args(argv)
    configure_logging(args.log_level or "INFO")
    try:
        from .config import apply_vea_config
        apply_vea_config(args, args.command_parser, args.command_name)
        configure_logging(args.log_level or "INFO")
        return args.handler(args)
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
        logger.info("error: %s", error)
        return 1
