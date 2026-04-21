"""Project-wide logging configuration helpers."""

import logging
import os
import sys


def configure_logging(name="womens_cricket_analytics"):
    """Configure and return a console logger for the application."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    logger.setLevel(log_level)
    logger.addHandler(handler)
    logger.propagate = False

    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(log_level)

    return logger