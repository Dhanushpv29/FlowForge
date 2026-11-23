import logging

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once; safe to call repeatedly."""
    logging.basicConfig(level=level.upper(), format=LOG_FORMAT, force=True)
