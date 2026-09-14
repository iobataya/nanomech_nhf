"""Analysis outcomes shared by CLI and GUI, without process exit codes."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .preparation import CalibrationPreparation
    from .selection import PointSelection
    from .excitation import ExcitationFitResult as ExcitationModelResult


@dataclass(frozen=True)
class VeaResult:
    status: str
    output_dir: Path | None
    selection: "PointSelection"
    preparation: "CalibrationPreparation"
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ExcitationFitResult:
    status: str
    output_dir: Path
    fit: "ExcitationModelResult"
    metadata: dict
