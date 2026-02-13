# utils/logging.py
import logging
import os


def setup_logging(debug_mode: bool = None) -> None:
    """
    Setup logging configuration.

    Args:
        debug_mode: Override debug mode. If None, reads from LOG_LEVEL env var.
                   LOG_LEVEL can be: DEBUG, INFO, WARNING, ERROR, CRITICAL
    """
    if debug_mode is None:
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    else:
        log_level = "DEBUG" if debug_mode else "INFO"

    level = getattr(logging, log_level, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
