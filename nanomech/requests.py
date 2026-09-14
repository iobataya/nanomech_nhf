"""Interface-independent analysis conditions; all values use SI units."""
from dataclasses import dataclass, field
from pathlib import Path

from .preparation import positive
from .static import StaticConfig


@dataclass(frozen=True)
class ProbeOverrides:
    sensitivity: float | None = None
    spring_constant: float | None = None

    def validate(self):
        for name in ("sensitivity", "spring_constant"):
            value = getattr(self, name)
            if value is not None:
                positive(value, name)


@dataclass(frozen=True)
class VeaRequest:
    sample: Path
    calibration: Path | None = None
    output: Path = Path("results")
    static: StaticConfig = field(default_factory=StaticConfig)
    max_count: int | None = None
    crop_area: str | None = None
    dry_run: bool = False
    plot_calibration: bool = False
    plot_sample: bool = False
    max_plot_sample: int | None = None
    excitation: str = "auto"
    correct_drag: bool = True
    probe: ProbeOverrides = field(default_factory=ProbeOverrides)
    probe_config: ProbeOverrides = field(default_factory=ProbeOverrides)
    probe_source: str = "API"
    config_path: Path | None = None

    def validate(self):
        if not self.sample:
            raise ValueError("sample is required")
        self.static.validate()
        self.probe.validate()
        self.probe_config.validate()
        for name, minimum in (("max_count", 1), ("max_plot_sample", 0)):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < minimum):
                qualifier = "positive" if minimum else "nonnegative"
                raise ValueError(f"{name} must be a {qualifier} integer")
        for name in ("dry_run", "plot_calibration", "plot_sample", "correct_drag"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be a boolean")
        if self.excitation not in ("auto", "Piezo", "CleanDrive"):
            raise ValueError("excitation must be auto, Piezo or CleanDrive")


@dataclass(frozen=True)
class ExcitationFitRequest:
    source: Path
    output: Path = Path("results")
    config_path: Path | None = None

    def validate(self):
        if not self.source:
            raise ValueError("source is required")
