"""Project-wide logging configuration helpers."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def configure_logging(name="womens_cricket_analytics"):
    """Configure and return a logger with console and file handlers."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Enhanced formatter with more context
    detailed_format = (
        "[%(asctime)s] %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
    )
    simple_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    
    formatter_console = logging.Formatter(simple_format, datefmt="%Y-%m-%d %H:%M:%S")
    formatter_file = logging.Formatter(detailed_format, datefmt="%Y-%m-%d %H:%M:%S")

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter_console)
    console_handler.setLevel(log_level)

    # File handler with rotation (5 files, 5MB each)
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    log_file = os.path.join(logs_dir, f"{name}.log")
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5
    )
    file_handler.setFormatter(formatter_file)
    file_handler.setLevel(logging.DEBUG)

    # Configure logger
    logger.setLevel(logging.DEBUG)  # Logger accepts all, handlers filter
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.propagate = False

    # Configure werkzeug logger separately to avoid Flask request spam
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(log_level)
    
    # Only add werkzeug to console at WARNING level
    werkzeug_console = logging.StreamHandler(sys.stdout)
    werkzeug_console.setFormatter(formatter_console)
    werkzeug_console.setLevel(logging.WARNING)
    werkzeug_logger.addHandler(werkzeug_console)

    logger.info("Logging configured: level=%s, log_file=%s", log_level_name, log_file)
    return logger