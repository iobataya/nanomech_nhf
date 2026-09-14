"""Qt-independent, per-stage progress notifications."""
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisProgress:
    stage: str
    completed: int = 0
    total: int | None = None

    @property
    def percent(self) -> float | None:
        """None means this stage has no measurable point count (e.g. saving)."""
        if self.total is None:
            return None
        return 100.0 * self.completed / self.total if self.total else 100.0


ProgressCallback = Callable[[AnalysisProgress], None]
PointProgressCallback = Callable[[int, int], None]


def iter_progress(points, callback: PointProgressCallback | None = None):
    """Count completed attempts, including handled failures and skipped points.

    The caller processes each yielded point before notification. An unhandled
    exception aborts iteration without falsely reporting that point complete.
    """
    total = len(points)
    if callback is not None:
        callback(0, total)
    for completed, point in enumerate(points, 1):
        yield point
        if callback is not None:
            callback(completed, total)
