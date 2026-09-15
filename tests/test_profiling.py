import csv
import json
import pstats
import sys
from types import SimpleNamespace

import pytest

from nanomech.profiling import main, profile_run


def test_call_counts_and_reports(tmp_path):
    def leaf():
        return sum(range(10))

    with profile_run(tmp_path, metadata={"case": "small"}) as directory:
        for _ in range(7):
            leaf()
    stats = pstats.Stats(str(directory / "profile.pstats"))
    entry = next(value for key, value in stats.stats.items() if key[2] == "leaf")
    assert entry[:2] == (7, 7)
    with (directory / "functions.csv").open(encoding="utf-8-sig", newline="") as stream:
        row = next(row for row in csv.DictReader(stream) if row["function"] == "leaf")
    assert int(row["total_calls"]) == 7
    assert float(row["cumulative_seconds"]) >= float(row["self_seconds"]) >= 0
    details = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    assert details["elapsed_seconds"] > 0
    assert details["status"] == "completed"
    assert details["metadata"] == {"case": "small"}
    assert "Elapsed wall time" in (directory / "summary.txt").read_text()


def test_exception_still_saves_and_runs_do_not_overwrite(tmp_path):
    with pytest.raises(ValueError, match="analysis failed"):
        with profile_run(tmp_path) as failed:
            raise ValueError("analysis failed")
    with profile_run(tmp_path) as completed:
        pass
    assert failed != completed
    assert (failed / "profile.pstats").is_file()
    assert json.loads((failed / "run.json").read_text())["status"] == "failed"


def test_cli_forwards_arguments_and_exit_code(tmp_path, monkeypatch):
    received = []

    def fake_main(argv):
        received.extend(argv)
        return 1

    monkeypatch.setitem(sys.modules, "nanomech.cli", SimpleNamespace(main=fake_main))
    assert main(["--output", str(tmp_path), "--", "vea", "--max-count", "4"]) == 1
    assert received == ["vea", "--max-count", "4"]
    details = json.loads(next(tmp_path.glob("*/run.json")).read_text())
    assert details["metadata"]["exit_code"] == 1
