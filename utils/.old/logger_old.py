# utils/logger.py
import logging
from pathlib import Path
from datetime import datetime

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

def setup_logger(name: str, filename: str = "pipeline.log", to_console: bool = False) -> logging.Logger:
    log_path = LOG_DIR / filename
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers
    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s')

        # File handler
        fh = logging.FileHandler(log_path)
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        # Optional console handler
        if to_console:
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            ch.setFormatter(formatter)
            logger.addHandler(ch)

    return logger

def get_timestamp_str() -> str:
    """Returns UTC timestamp for filenames/logs."""
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
