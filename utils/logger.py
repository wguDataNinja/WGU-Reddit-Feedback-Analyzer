# Filename: utils/logger.py

import logging
from pathlib import Path
from datetime import datetime, timezone


def setup_logger(
    name: str,
    filename: str = "pipeline.log",
    to_console: bool = False,
    verbose: bool = False,
) -> logging.Logger:
    log_path = Path(filename)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Avoid duplicate handlers
    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s')

        # File handler (always logs everything)
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        # Optional console handler
        if to_console:
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG if verbose else logging.INFO)
            ch.setFormatter(formatter)
            logger.addHandler(ch)

    return logger


def get_timestamp_str() -> str:
    """Returns UTC timestamp for filenames/logs."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")