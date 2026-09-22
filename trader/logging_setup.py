"""Configures logging for the whole application.

Logging is like a diary the program writes as it runs. Each line has a
timestamp, a severity level, and which part of the program wrote it:

    2026-09-22 14:30:05 | INFO    | trader.main | Loaded 3 symbols

Messages go to two places: the terminal (so you can watch) and a log file
(so you can look back later).
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str, log_file: Path) -> None:
    """Send log messages to both the terminal and a log file."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    # "Rotating" = when the file reaches ~1 MB, start a new one and keep 5 old ones,
    # so logs can never fill up your disk.
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(console)
    root.addHandler(file_handler)
