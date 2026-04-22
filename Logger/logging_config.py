"""Project-wide logging configuration helpers."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def get_log_file_path():
    """Resolve and ensure the configured log file path."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.getenv("LOG_DIR", os.path.join(base_dir, "logs"))
    log_file_name = os.getenv("LOG_FILE_NAME", "app.log")
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, log_file_name)


def configure_logging(name="womens_cricket_analytics"):
    """Configure and return a console + rotating file logger for the application."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = None
    try:
        max_bytes = int(os.getenv("LOG_MAX_BYTES", "1048576"))
        backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))
        file_handler = RotatingFileHandler(
            get_log_file_path(),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
    except (ValueError, OSError):
        file_handler = None

    logger.setLevel(log_level)
    logger.addHandler(console_handler)
    if file_handler is not None:
        logger.addHandler(file_handler)
    logger.propagate = False

    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(log_level)

    return logger