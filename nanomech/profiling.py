"""Opt-in, current-thread profiling with standard-library report formats."""
import argparse
from contextlib import contextmanager
import cProfile
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import pstats
import sys
from time import perf_counter


@contextmanager
def profile_run(output="profiles", *, metadata=None):
    """Profile this thread and save a new run directory, including on failure.

    Enter inside the worker when measuring a GUI workflow. Report generation is
    excluded from the measurement. Exceptions from the measured code propagate.
    """
    from tempfile import mkdtemp

    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    directory = Path(mkdtemp(prefix=started.strftime("%Y%m%dT%H%M%SZ-"), dir=root))
    profiler = cProfile.Profile()
    status = "failed"
    start = perf_counter()
    profiler.enable()
    try:
        yield directory
        status = "completed"
    finally:
        profiler.disable()
        elapsed = perf_counter() - start
        profiler.dump_stats(str(directory / "profile.pstats"))
        stats = pstats.Stats(profiler)
        with (directory / "functions.csv").open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            writer.writerow(["file", "line", "function", "primitive_calls", "total_calls",
                             "self_seconds", "cumulative_seconds"])
            for (filename, line, function), (primitive, total, own, cumulative, _) in sorted(
                    stats.stats.items(), key=lambda item: item[1][3], reverse=True):
                writer.writerow([filename, line, function, primitive, total, own, cumulative])
        with (directory / "summary.txt").open("w", encoding="utf-8") as stream:
            stream.write(f"Elapsed wall time: {elapsed:.6f} seconds\n")
            stats.stream = stream
            for key in ("cumulative", "tottime", "calls"):
                stats.sort_stats(key).print_stats(50)
        details = {
            "schema_version": 1,
            "started_at": started.isoformat(),
            "status": status,
            "elapsed_seconds": elapsed,
            "python": sys.version,
            "platform": platform.platform(),
            "cwd": str(Path.cwd()),
            "metadata": metadata or {},
        }
        (directory / "run.json").write_text(
            json.dumps(details, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Profile the nanomech CLI (pass its arguments after --).")
    parser.add_argument("--output", type=Path, default=Path("profiles"),
                        help="Parent directory for profiling reports (default: profiles)")
    parser.add_argument("cli_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    cli_args = args.cli_args
    if cli_args[:1] == ["--"]:
        cli_args = cli_args[1:]
    if not cli_args:
        parser.error("Pass nanomech CLI arguments after --")
    metadata = {"cli_args": cli_args}
    with profile_run(args.output, metadata=metadata) as directory:
        print(f"Profiling reports: {directory.resolve()}", file=sys.stderr)
        from .cli import main as cli_main
        result = cli_main(cli_args)
        metadata["exit_code"] = result
    return result


if __name__ == "__main__":
    raise SystemExit(main())
