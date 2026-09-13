"""Console logging setup for application entry points."""
import logging


def configure_logging(level="INFO"):
    """Apply the selected level without replacing existing handlers."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logging.getLogger().setLevel(level)
